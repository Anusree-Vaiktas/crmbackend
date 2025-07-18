from rest_framework.pagination import PageNumberPagination

class CustomUserPagination(PageNumberPagination):
    page_size = None
    page_size_query_param = 'page_size'

    def get_next_page_number(self, page):
        return page.next_page_number() if page.has_next() else None

    def get_previous_page_number(self, page):
        return page.previous_page_number() if page.has_previous() else None

def paginate_and_format_response(paginated_data, request, pagination_class):
    paginator = pagination_class()
    page = paginator.paginate_queryset(paginated_data, request)

    if page is not None:
        page_size = int(request.query_params.get('page_size', paginator.page_size))
        return {
            'total': paginator.page.paginator.count,
            'page': paginator.page.number,
            'page_size': page_size,
            'next_page': paginator.get_next_page_number(paginator.page),
            'previous_page': paginator.get_previous_page_number(paginator.page),
            'Details': page
        }, None

    return {
        'total': len(paginated_data),
        'page': 1,
        'page_size': len(paginated_data),
        'next_page': None,
        'previous_page': None,
        'Details': paginated_data
    }, None
