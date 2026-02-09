from flask import Blueprint, jsonify, request
from models.onboarding_model import OnboardingModel

onboarding_bp = Blueprint('onboarding', __name__)
model = OnboardingModel()

@onboarding_bp.route('/api/onboarding/steps', methods=['GET'])
def get_steps():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    steps = model.get_user_steps(user_id)
    return jsonify(steps), 200

@onboarding_bp.route('/api/onboarding/update', methods=['POST'])
def update_step_status():
    data = request.json
    user_id = data.get('user_id')
    step_id = data.get('step_id')
    status = data.get('status') # 'completed' or 'pending'

    if not all([user_id, step_id, status]):
        return jsonify({"error": "Missing required fields"}), 400

    success = model.update_progress(user_id, step_id, status)
    if success:
        return jsonify({"message": "Status updated successfully"}), 200
    return jsonify({"error": "Failed to update status"}), 500

@onboarding_bp.route('/api/onboarding/progress', methods=['GET'])
def get_progress():
    user_id = request.args.get('user_id')
    progress = model.get_overall_progress(user_id)
    return jsonify({"progress": progress}), 200
