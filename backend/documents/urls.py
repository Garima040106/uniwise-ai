from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_document, name="upload_document"),
    path("list/", views.list_documents, name="list_documents"),
    path("<int:doc_id>/", views.document_detail, name="document_detail"),
    path("<int:doc_id>/delete/", views.delete_document, name="delete_document"),
]
