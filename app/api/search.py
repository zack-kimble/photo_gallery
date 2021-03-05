from app import bp

@bp.route('/api/search/<int:search-id>', methods=['GET'])
def get_search():
    pass

@bp.route('/api/search/<int:search-id>/results', methods=['GET'])
def get_search_results():
    pass