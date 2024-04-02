from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from flask import session
from flask import json
from bson import json_util
from bson import ObjectId





import os

# Generate secret key if not already set

app = Flask(__name__)
if 'SECRET_KEY' not in os.environ:
    os.environ['SECRET_KEY'] = os.urandom(24).hex()
else:
    app.secret_key = os.environ['SECRET_KEY']
# MongoDB connection
client = MongoClient("mongodb+srv://Sharnitha:Sharnitha_27@cluster0.il7urpc.mongodb.net/")
db = client.get_database('Blogging')
users_collection = db.users
posts_collection = db.posts
comments_collection = db.comments
followers_collection = db['followers']


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_id = request.form['user_id']  # Get user ID from the form
        

        # Check if the user already exists
        existing_user = users_collection.find_one({'email': email})

        if existing_user:
            flash('Email address already exists. Please try with a different email.')
            return redirect(url_for('signup'))

        # Create new user
        new_user = {
            'username': username,
            'email': email,
            'password': password,
            'user_id': user_id  # Include user ID in the user document
        }

        # Insert user data into MongoDB
        users_collection.insert_one(new_user)

        flash('You have successfully signed up!','success')
        return redirect(url_for('signup'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if user exists in the database
        user = users_collection.find_one({'email': email, 'password': password})

        if user:
            # Convert _id field to string if it's an ObjectId
            if isinstance(user['_id'], ObjectId):
                user['_id'] = str(user['_id'])

            # Store user data in session
            session['user'] = user
            flash('Login successful!', 'success')

            # Render dashboard template directly
            return render_template('dashboard.html', user=user)
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if user_id:
        try:
            user_id = ObjectId(user_id)  # Attempt conversion to ObjectId
            user = users_collection.find_one({'_id': user_id})
            if user:
                return render_template('dashboard.html', user=user)
        except ObjectId.InvalidId:
            flash('Invalid user ID format.', 'error')
            session.pop('user_id', None)  # Clear invalid session data
            return redirect(url_for('login'))
    flash('You need to login first.', 'error')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()
    flash('You have been logged out successfully!', 'success')
    
    
    # Redirect the user to the login page or any other desired page
    return redirect(url_for('login'))

    


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    # Check if the user is logged in
    if 'user_id' not in session:
        flash('You need to login first.', 'error')
        return redirect(url_for('login'))

    # Retrieve user ID from session
    user_id = session['user_id']

    # Check if the user ID is valid
    try:
        user_id = ObjectId(user_id)
    except ObjectId.InvalidId:
        flash('Invalid user ID format.', 'error')
        session.pop('user_id', None)  # Clear invalid session data
        return redirect(url_for('login'))

    # Fetch user data from the database
    user = users_collection.find_one({'_id': user_id})

    if not user:
        flash('User not found.', 'error')
        session.pop('user_id', None)  # Clear invalid session data
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Retrieve form data
        new_username = request.form['username']
        new_email = request.form['email']
        
        # Update user profile in the database
        result = users_collection.update_one(
            {'_id': user_id},
            {'$set': {'username': new_username, 'email': new_email}}
        )

        if result.modified_count > 0:
            flash('Profile updated successfully!', 'success')
        else:
            flash('Failed to update profile. Please try again.', 'error')

        # Redirect to the dashboard page after profile update
        return redirect(url_for('dashboard'))

    # Render the edit profile page with user data
    return render_template('edit_profile.html', user=user)


# Route for creating a new post
@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author_id = request.form['author_id']  # Get author ID from the form

        # Create new post document
        new_post = {
            'title': title,
            'content': content,
            'author_id': author_id,  # Use the author ID obtained from the form
        }

        # Insert the new post document into the posts collection
        result = posts_collection.insert_one(new_post)

        flash('Post created successfully!', 'success')
        return redirect(url_for('dashboard'))  # Redirect to dashboard or posts page

    return render_template('create_post.html')

@app.route('/view_posts_page')
def view_posts_page():
    return render_template('view_post.html')

@app.route('/view_posts', methods=['POST'])
def view_posts():
    author_id = request.form['author_id']
    
    # Fetch posts by author ID
    author_posts = posts_collection.find({'author_id': author_id})
    
    return render_template('view_post.html', author_posts=author_posts)


@app.route('/delete_post', methods=['POST'])
def delete_post():
    author_id = request.form.get('author_id')  # Get author ID from the form

    # Delete posts with the specified author ID
    result = posts_collection.delete_many({'author_id': author_id})

    if result.deleted_count > 0:
        flash('Posts deleted successfully!', 'success')
    else:
        flash('No posts found for the specified author ID.', 'error')

    return redirect(url_for('dashboard'))

@app.route('/delete_post_page')
def delete_post_page():
    return render_template('delete_post.html')






# Route to render the comment form
@app.route('/comment_form')
def comment_form():
    return render_template('add_comment.html')

# Route to handle adding comments
@app.route('/add_comment', methods=['POST'])
def add_comment():
    # Retrieve author ID, post ID, and comment content from the form
    author_id = request.form.get('author_id')
    post_id = request.form.get('post_id')
    comment_content = request.form.get('content')

    # Create a new comment document
    new_comment = {
        'author_id': author_id,
        'post_id': post_id,
        'content': comment_content
    }

    # Insert the new comment document into the comments collection
    comments_collection.insert_one(new_comment)

    flash('Comment added successfully!', 'success')
    return redirect(url_for('dashboard'))

## Combined route to handle deletion of a comment and render delete comment page
@app.route('/remove_comment', methods=['GET', 'POST'])
def remove_comment():
    if request.method == 'POST':
        author_id = request.form.get('author_id')    # Get author ID from the form

        # Attempt to delete the comment from the database if it matches the author ID
        result = comments_collection.delete_one({'author_id': author_id})

        # Check if the comment was successfully deleted
        if result.deleted_count > 0:
            flash('Comment deleted successfully!', 'success')
        else:
            flash('No comment found for the specified ID or you are not authorized to delete this comment.', 'error')

        return redirect(url_for('dashboard'))
    else:
        return render_template('remove_comment.html')
    

    
# Route for the user's feed
@app.route('/feed')
def feed():
    user_id = session.get('user_id')
    if user_id:
        following_ids = [doc['followed_user_id'] for doc in followers_collection.find({'follower_id': user_id})]
        feed_posts = posts_collection.find({'author_id': {'$in': following_ids}})
        return render_template('feed.html', feed_posts=feed_posts)
    flash('You need to login first.', 'error')
    return redirect(url_for('login'))








if __name__ == '__main__':
    app.run(debug=True)
