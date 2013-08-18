# coding: utf-8
import datetime
import time
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.utils.html import escape
from reviews.models import Review, Source, Article, Question, SelectionCriteria
from pybtex.database.input import bibtex

@login_required
def reviews(request, username):
    context = RequestContext(request)
    user = get_object_or_404(User, username=username)
    user_reviews = Review.objects.filter(author__id=user.id).order_by('-last_update',)
    context = RequestContext(request, {'user_reviews': user_reviews, 'page_user': user})
    return render_to_response('reviews/reviews.html', context)

@login_required
def new(request):
    if request.method == 'POST':
        name = request.POST['name']
        title = request.POST['title']
        description = request.POST['description']
        author = request.user
        last_update = datetime.date.today()
        review = Review(name = name, title = title, description = description, author=author, last_update=last_update)
        review.save()
        messages.add_message(request, messages.SUCCESS, 'Review created with success.')
        return redirect('/' + request.user.username + '/')
    else:
        context = RequestContext(request)
        return render_to_response('reviews/new.html', context)

@login_required
def review(request, username, review_name):
    review = Review.objects.get(name=review_name, author__username=username)
    context = RequestContext(request, {'review': review})
    return render_to_response('reviews/review.html', context)

@login_required
def add_author_to_review(request):
    username = request.GET['username']
    review_id = request.GET['id']
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    if user is not None:
        review = Review.objects.get(pk=review_id)
        if review.author.id == request.user.id:
            review.co_authors.add(user)
            review.save()
            return HttpResponse('<li author-id="' + str(user.id) + '"><a href="/' + user.username +'/">' + user.get_full_name() + '</a> <button type="button" class="remove-author">(remove)</button></li>')
        else:
            return HttpResponse('error')
    else:
        return HttpResponse('error')

@login_required
def remove_author_from_review(request):
    author_id = request.GET['author_id']
    review_id = request.GET['review_id']
    author = User.objects.get(pk=author_id)
    review = Review.objects.get(pk=review_id)
    review.co_authors.remove(author)
    review.save()
    return HttpResponse('OK')

@login_required
def planning(request, username, review_name):
    review = Review.objects.get(name=review_name, author__username=username)
    context = RequestContext(request, {'review': review })
    return render_to_response('reviews/planning.html', context)

@login_required
def conducting(request, username, review_name):
    parser = bibtex.Parser()
    bibdata = parser.parse_file("/Users/vitorfs/Downloads/scopus.bib")

    articles = []
    for bib_id in bibdata.entries:
        b = bibdata.entries[bib_id].fields
        article = Article()

        try:
            article.title = b["title"]
            article.journal = b["journal"]
            article.year = b["year"]
            article.author = b["author"]
            article.id = bib_id
        except(KeyError):
            continue

        articles.append(article)

    review = Review.objects.get(name=review_name, author__username=username)
    context = RequestContext(request, {'review': review, 'articles': articles})
    return render_to_response('reviews/conducting.html', context)

@login_required
def reporting(request, username, review_name):
    review = Review.objects.get(name=review_name, author__username=username)
    context = RequestContext(request, {'review': review})
    return render_to_response('reviews/reporting.html', context)

@login_required
def add_source_to_review(request):
    '''
        Function used via Ajax request only.
        This function adds a new source to the source list of the review.
        To add the source successfully the logged in user must be the author or a co-author
        of the review.
    '''
    review_id = request.GET['id']
    name = request.GET['name']
    url = request.GET['url']
    source = Source(name=name, url=url)
    source.save()

    review = Review.objects.get(pk=review_id)
    if review.author.id == request.user.id:
        review.sources.add(source)
        review.save()
        return_html = '<tr source-id="' + str(source.id) + '"><td>' + escape(source.name) + '</td><td>' + escape(source.url) + '</td><td><button type="button" class="btn btn-small">edit</button> <button type="button" class="btn btn-warning btn-small btn-remove-source">remove</a></td></tr>'
        return HttpResponse(return_html)
    else:
        return HttpResponse('error')

@login_required
def remove_source_from_review(request):
    '''
        Function used via Ajax request only.
    '''
    source_id = request.GET['source_id']
    review_id = request.GET['review_id']
    source = Source.objects.get(pk=source_id)
    review = Review.objects.get(pk=review_id)
    review.sources.remove(source)
    source.delete()
    review.save()
    return HttpResponse('OK')

@login_required
def save_question(request):
    '''
        Function used via Ajax request only.
        This function takes a review question form and save on the database
    '''
    if request.method == 'POST':
        prefix = str(request.POST['prefix'])
        review_id = request.POST['review-id']
        question_id = request.POST['question-id']
        question_type = request.POST['question-type']

        description = request.POST[prefix + 'question-description']
        population = request.POST[prefix + 'question-population']
        intervention = request.POST[prefix + 'question-intervention']
        comparison = request.POST[prefix + 'question-comparison']
        outcome = request.POST[prefix + 'question-outcome']

        review = Review.objects.get(pk=review_id)

        question = Question()

        if question_type == 'M':
            question = review.get_main_question()
        elif question_id != 'None':
            try:
                question = Question.objects.get(pk=question_id)
            except Question.DoesNotExist:
                pass

        question.review = review
        question.question = description
        question.population = population
        question.intervention = intervention
        question.comparison = comparison
        question.outcome = outcome
        question.question_type = question_type

        question.save()

        return HttpResponse(question.id)
    return HttpResponse('ERROR')

@login_required
def add_question(request):
    '''
        Function used via Ajax request only.
        This functions adds a new secondary question to the review.
    '''
    review_id = request.GET['review-id']
    review = Review.objects.get(pk=review_id)
    question = Question()
    prefix = int(time.time())
    context = RequestContext(request, {'review': review, 'question': question, 'question_type':'S', 'prefix':prefix})
    return render_to_response('reviews/planning_question.html', context)

@login_required
def remove_question(request):
    '''
        Function used via Ajax request only.
        This function removes a secondary question from the review.
    '''
    if request.method == 'POST':
        review_id = request.POST['review-id']
        question_id = request.POST['question-id']
        question_type = request.POST['question-type']

        if question_id != 'None' and question_type != 'M':
            try:
                question = Question.objects.get(pk=question_id)
                question.delete()
            except Question.DoesNotExist:
                return HttpResponse('ERROR')

        return HttpResponse('OK')
    return HttpResponse('ERROR')

@login_required
def save_question(request):
    '''
        Function used via Ajax request only.
    '''
    if request.method == 'POST':
        review_id = request.POST['review-id']
        objective = request.POST['objective']
        review = Review.objects.get(pk=review_id)
        review.objective = objective
        review.save()
    return HttpResponse('')

@login_required
def add_criteria(request):
    '''
        Function used via Ajax request only.
    '''
    review_id = request.GET['review-id']
    criteria = request.GET['criteria']
    criteria_type = request.GET['criteria-type']
    review = Review.objects.get(pk=review_id)
    if review.author.id == request.user.id:
        criteria = SelectionCriteria(review=review, description=criteria, criteria_type=criteria_type)
        criteria.save()
    return HttpResponse('')