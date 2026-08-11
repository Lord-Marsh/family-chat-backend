import os
from flask import Blueprint, request, jsonify, Response
from app import get_db
from app.utils.auth import token_required, create_jwt_token
from app.utils.id_generator import generate_login_log_id
from datetime import datetime
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
    AuthenticatorAttachment
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
        {"id": base64url_to_bytes(cred['credential_id']), "type": "public-key"}
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
            user_verification=UserVerificationRequirement.REQUIRED
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
    data = request.get_json()
    username = data.get('username')
    if not username:
        return jsonify({'message': 'Username is required'}), 400
        
    db = get_db()
    user = db.users.find_one({'username': username})
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    credentials = user.get('webauthn_credentials', [])
    if not credentials:
        return jsonify({'message': 'No fingerprints registered for this user'}), 400
        
    allow_credentials = [
        {"id": base64url_to_bytes(cred['credential_id']), "type": "public-key"}
        for cred in credentials
    ]
    
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED
    )
    
    challenge_str = base64.urlsafe_b64encode(options.challenge).decode('utf-8')
    db.users.update_one(
        {'_id': user['_id']},
        {'$set': {'current_webauthn_challenge': challenge_str}}
    )
    
    return Response(options_to_json(options), mimetype='application/json')

@webauthn_bp.route('/login/verify', methods=['POST'])
def login_verify():
    origin, rp_id = get_origin_and_rp_id()
    data = request.get_json()
    username = data.get('username')
    credential_data = data.get('credential')
    
    if not username or not credential_data:
        return jsonify({'message': 'Missing data'}), 400
        
    db = get_db()
    user = db.users.find_one({'username': username})
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    expected_challenge = user.get('current_webauthn_challenge')
    if not expected_challenge:
        return jsonify({'message': 'No challenge found'}), 400
        
    # Find the specific credential
    credentials = user.get('webauthn_credentials', [])
    matching_cred = None
    
    # We need to pad the incoming credential.id with '=' if necessary
    incoming_id = credential_data.get('id', '')
    for cred in credentials:
        if cred['credential_id'] == incoming_id or cred['credential_id'] == incoming_id.rstrip('='):
            matching_cred = cred
            break
            
    if not matching_cred:
        return jsonify({'message': 'Credential not registered for this user'}), 400

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
            {
                '$set': {'webauthn_credentials.$.sign_count': verification.new_sign_count},
                '$unset': {'current_webauthn_challenge': ""}
            }
        )
        
        # Generate token
        token = create_jwt_token(user['_id'])
        
        # Log success
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
        # Log failure
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
