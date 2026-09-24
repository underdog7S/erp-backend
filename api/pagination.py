from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Site-wide list pagination.

    Most screens read `response.data.results` as if it were the whole list and
    have no page controls, so the old default of 10 rows silently hid everything
    after the tenth record. 200 covers normal small-business lists; callers that
    do paginate can still ask for `?page_size=` (up to 1000) and follow `next`.
    """
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 1000
