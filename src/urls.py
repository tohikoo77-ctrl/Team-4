from django.urls import path
from src.views.transfer_views import transfer_rpc

urlpatterns = [
    path("api/transfer/", transfer_rpc, name="transfer_rpc"),
]