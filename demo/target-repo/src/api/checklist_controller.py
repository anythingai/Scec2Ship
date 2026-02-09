from flask import Blueprint, request, jsonify
from src.models.checklist_model import ChecklistStep, UserChecklistProgress

checklist_bp = Blueprint('checklist', __name__)

@checklist_bp.route('/api/checklist', methods=['GET'])
def get_checklist():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    steps = ChecklistStep.query.order_by(ChecklistStep.order_index).all()
    progress = UserChecklistProgress.query.filter_by(user_id=user_id).all()
    
    progress_map = {p.step_id: p.completed for p in progress}
    
    result = []
    for step in steps:
        result.append({
            'id': step.id,
            'title': step.title,
            'description': step.description,
            'link': step.link,
            'completed': progress_map.get(step.id, False)
        })
    return jsonify(result)

@checklist_bp.route('/api/checklist/update', methods=['POST'])
def update_progress():
    data = request.json
    user_id = data.get('user_id')
    step_id = data.get('step_id')
    completed = data.get('completed')
    
    progress = UserChecklistProgress.query.filter_by(user_id=user_id, step_id=step_id).first()
    if not progress:
        progress = UserChecklistProgress(user_id=user_id, step_id=step_id)
    
    progress.completed = completed
