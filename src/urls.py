from django.urls import path

from src.views.credit import credit_request_api
from src.views.transfer_views import transfer_rpc
from src.views.register import register_view

urlpatterns = [
    path("api/transfer/", transfer_rpc, name="transfer_rpc"),
    path('register/', register_view, name='register'),
    path('credit/request/', credit_request_api, name='credit_request'),
]
