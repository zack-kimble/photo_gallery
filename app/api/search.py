from app.api import bp

@bp.route('/api/search/<int:search_id>', methods=['GET'])
def get_search():
    pass

@bp.route('/api/search/<int:search_id>/results', methods=['GET'])
def get_search_results():
    pass