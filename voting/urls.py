from django.urls import path
from . import views

urlpatterns = [
    # Now the full path will be /api/elections/ (POST for creating)
    path('', views.create_election, name='create_election'),
    # Full path: /api/elections/<id>/vote/ (POST for voting)
    path('<int:election_id>/vote/', views.cast_vote, name='cast_vote'),
    # Full path: /api/elections/<id>/results/ (GET for results)
    path('<int:election_id>/results/', views.election_results, name='election_results'),
]