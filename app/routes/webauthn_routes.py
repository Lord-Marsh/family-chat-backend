import os
from flask import Blueprint, request, jsonify, Response
from app import get_db
from app.utils.auth import token_required, create_jwt_token
from app.utils.id_generator import generate_login_log_id
from datetime import datetime, timedelta
import pytz
import base64
import json

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    options_to_json,
    generate_authentication_options,
    verify_authentication_response,
    base64url_to_bytes
)
from webauthn.helpers.structs import (
    RegistrationCredential,
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AuthenticatorAttachment,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement
)

webauthn_bp = Blueprint('webauthn', __name__)
IST = pytz.timezone('Asia/Kolkata')
RP_NAME = 'SplitPay'

def get_origin_and_rp_id():
    origin = request.headers.get('Origin')
    if not origin:
        origin = 'http://localhost:5173'
    rp_id = origin.replace('https://', '').replace('http://', '').split(':')[0]
    return origin, rp_id

@webauthn_bp.route('/register/generate', methods=['GET'])
@token_required
def register_generate(current_user_id):
    origin, rp_id = get_origin_and_rp_id()
    db = get_db()
    user = db.users.find_one({'_id': current_user_id})
    if not user:
        return jsonify({'message': 'User not found'}), 404

    existing_credentials = user.get('webauthn_credentials', [])
    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred['credential_id']))
        for cred in existing_credentials
    ]

    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=RP_NAME,
        user_id=str(user['_id']).encode('utf-8'),
        user_name=user['username'],
        user_display_name=user.get('displayName', user['username']),
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            user_verification=UserVerificationRequirement.REQUIRED,
            resident_key=ResidentKeyRequirement.REQUIRED
        )
    )

    challenge_str = base64.urlsafe_b64encode(options.challenge).decode('utf-8')
    db.users.update_one(
        {'_id': current_user_id},
        {'$set': {'current_webauthn_challenge': challenge_str}}
    )

    return Response(options_to_json(options), mimetype='application/json')

@webauthn_bp.route('/register/verify', methods=['POST'])
@token_required
def register_verify(current_user_id):
    origin, rp_id = get_origin_and_rp_id()
    data = request.get_json()
    db = get_db()
    user = db.users.find_one({'_id': current_user_id})
    
    expected_challenge = user.get('current_webauthn_challenge')
    if not expected_challenge:
        return jsonify({'message': 'No challenge found'}), 400

    try:
        verification = verify_registration_response(
            credential=data,
            expected_challenge=base64url_to_bytes(expected_challenge),
            expected_rp_id=rp_id,
            expected_origin=origin,
            require_user_verification=True
        )
        
        new_credential = {
            'credential_id': base64.urlsafe_b64encode(verification.credential_id).decode('utf-8').rstrip('='),
            'public_key': base64.urlsafe_b64encode(verification.credential_public_key).decode('utf-8'),
            'sign_count': verification.sign_count,
            'created_at': datetime.now(IST)
        }
        
        db.users.update_one(
            {'_id': current_user_id},
            {
                '$push': {'webauthn_credentials': new_credential},
                '$unset': {'current_webauthn_challenge': ""}
            }
        )
        
        return jsonify({'message': 'Fingerprint registered successfully'}), 200
        
    except Exception as e:
        return jsonify({'message': f'Verification failed: {str(e)}'}), 400

@webauthn_bp.route('/login/generate', methods=['POST'])
def login_generate():
    origin, rp_id = get_origin_and_rp_id()
    db = get_db()
    
    # We don't require a username anymore! Discoverable credentials allow an empty allow_credentials list.
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=[],
        user_verification=UserVerificationRequirement.REQUIRED
    )
    
    challenge_str = base64.urlsafe_b64encode(options.challenge).decode('utf-8')
    
    # Store the challenge globally since we don't know the user yet
    db.auth_challenges.insert_one({
        'challenge': challenge_str,
        'createdAt': datetime.now(IST)
    })
    
    # Clean up old challenges to prevent database bloat
    db.auth_challenges.delete_many({
        'createdAt': {'$lt': datetime.now(IST) - timedelta(minutes=10)}
    })
    
    return Response(options_to_json(options), mimetype='application/json')

@webauthn_bp.route('/login/verify', methods=['POST'])
def login_verify():
    origin, rp_id = get_origin_and_rp_id()
    data = request.get_json()
    credential_data = data.get('credential')
    
    if not credential_data:
        return jsonify({'message': 'Missing credential data'}), 400
        
    db = get_db()
    
    incoming_id = credential_data.get('id', '')
    user = db.users.find_one({
        '$or': [
            {'webauthn_credentials.credential_id': incoming_id},
            {'webauthn_credentials.credential_id': incoming_id.rstrip('=')}
        ]
    })
    
    if not user:
        return jsonify({'message': 'Unregistered fingerprint or device not recognized.'}), 404
        
    # Find the specific credential
    credentials = user.get('webauthn_credentials', [])
    matching_cred = next((c for c in credentials if c['credential_id'] in (incoming_id, incoming_id.rstrip('='))), None)
            
    if not matching_cred:
        return jsonify({'message': 'Credential mismatch'}), 400

    # Retrieve the challenge from our global collection. 
    # The client must send back the challenge they signed, or we just find ANY valid recent challenge?
    # Actually, verify_authentication_response requires exactly the expected challenge.
    # We can ask the client to send the challenge back, or we look it up by the base64url challenge in clientDataJSON.
    
    # Extract the challenge from the clientDataJSON
    client_data_json_b64 = credential_data.get('response', {}).get('clientDataJSON')
    if not client_data_json_b64:
        return jsonify({'message': 'Invalid response from authenticator'}), 400
        
    client_data_json = json.loads(base64url_to_bytes(client_data_json_b64).decode('utf-8'))
    expected_challenge = client_data_json.get('challenge')
    
    # Verify this challenge actually exists in our DB and is valid
    challenge_doc = db.auth_challenges.find_one_and_delete({'challenge': expected_challenge})
    if not challenge_doc:
        return jsonify({'message': 'Invalid or expired challenge'}), 400

    try:
        verification = verify_authentication_response(
            credential=credential_data,
            expected_challenge=base64url_to_bytes(expected_challenge),
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=base64url_to_bytes(matching_cred['public_key']),
            credential_current_sign_count=matching_cred['sign_count'],
            require_user_verification=True
        )
        
        # Update sign count
        db.users.update_one(
            {'_id': user['_id'], 'webauthn_credentials.credential_id': matching_cred['credential_id']},
            {'$set': {'webauthn_credentials.$.sign_count': verification.new_sign_count}}
        )
        
        token = create_jwt_token(user['_id'])
        
        success_log = {
            '_id': generate_login_log_id(),
            'userId': user['_id'],
            'username': user['username'],
            'displayName': user.get('displayName', user['username']),
            'action': 'login_success_biometric',
            'ipAddress': request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown'),
            'userAgent': request.headers.get('User-Agent', 'unknown'),
            'timestamp': datetime.now(IST)
        }
        db.login_logs.insert_one(success_log)
        
        return jsonify({
            'token': token,
            'user': {
                'id': user['_id'],
                'username': user['username'],
                'displayName': user.get('displayName', user['username']),
                'email': user.get('email'),
                'avatar': user.get('avatar'),
                'userType': user.get('userType', 'a')
            }
        }), 200
        
    except Exception as e:
        failed_log = {
            '_id': generate_login_log_id(),
            'userId': user['_id'],
            'username': user['username'],
            'displayName': user.get('displayName', user['username']),
            'action': 'login_failed_biometric',
            'ipAddress': request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown'),
            'userAgent': request.headers.get('User-Agent', 'unknown'),
            'timestamp': datetime.now(IST)
        }
        db.login_logs.insert_one(failed_log)
        return jsonify({'message': f'Authentication failed: {str(e)}'}), 400
