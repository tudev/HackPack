import cgi
import email
import hashlib
import json
import os
import requests
import smtplib
import uuid
from datetime import datetime, timedelta
from flask import (abort, jsonify, g, session, render_template, redirect,
                   request, url_for)
from functools import wraps
from manage import app, client, moment
from random import randint
from . import main


@main.before_request
def before_request():
    session.permanent = True
    g.user = None
    if 'user' in session:
        g.user = session['user']

@main.route('/')
def index():
    db = client.tudev_checkout
    
    inventory = db.inventory.find()
    inventory_list = []
    for item in inventory:
        formatted_item = '''
        <tr>
        <td>{name}</td>
        <td class="hide-col" id="{name}-quant">{quantity}</td>
        <td class="hide-col">{reservation_length}</td>
        <td class="hide-col">{item_category}</td>
        <td class="hide-col"><a href="{tutorials_link}">Link</a></td>
        <td>
            <form id="add-to-cart">
                <input type="number" name="cart_quanity" min="1"
                       max="{quantity}" placeholder="1"
                       id="cart_quantity" required>
                <input id="name" value="{name}" style="display: none" disabled>
                <button id="add_to_cart_b" type="submit"
                        style="background: none; border: none;">
                    <a>
                      Add to Cart
                      <i class="fa fa-shopping-cart" aria-hidden="true"></i>
                    </a>
                </button>
            </form>
        </td>
        </tr>
        '''.format(item_id=item['item_id'], name=item['name'],
                   quantity=item['quantity'],
                   reservation_length=item['reservation_length'],
                   item_category=item['category'],
                   tutorials_link=item['tutorials_link'])
        inventory_list.append(formatted_item)
    formatted_inventory = '\n'.join(inventory_list)

    hackathons = db.hackathons.find()
    hackathon_list = []
    for hackathon in hackathons:
        maps_link = 'https://www.google.com/maps/search/' + \
                    hackathon['location']
        formatted_hackathon = '''
        <tr>
            <td><a href="{link}" target="_blank">{name}</a></td>
            <td class="hide-col-h">
                <a href="{location_link}" target="_blank">{location}</a>
            </td>
            <td>{date}</td>
        </tr>
        '''.format(name=hackathon['name'], location=hackathon['location'],
                   location_link=maps_link, date=hackathon['date_range'],
                   link=hackathon['link'])
        hackathon_list.append(formatted_hackathon)
    formatted_hackathons = '\n'.join(hackathon_list)

    client_id = None
    welcome_msg = None
    user = None
    if g.user is None or 'user' not in session:
        client_id = app.config['CLIENT_ID']
    else:
        db = client.tudev_checkout
        found_user = db.users.find_one({'email': session['user']})
        user = session['user']
        if found_user:
            if found_user['email'] == 'shetyeshail@gmail.com':
                user = 'Cuff Boy'
            else:
                user = found_user['name'].split(' ')[0]
        random_msg_index = randint(0,len(app.config['WELCOME_MSG'])-1)
        welcome_msg = app.config['WELCOME_MSG'][random_msg_index]
    admin = False
    if 'user' in session:
        admin = session['user'] in app.config['ADMIN_EMAILS']
    return render_template('index.html', inventory=formatted_inventory,
                           hackathons=formatted_hackathons, user=user,
                           client_id=client_id, welcome_msg=welcome_msg,
                           admin=admin, host_url=request.host_url)

def admin_required(f):
    '''
        Allows the passed function to only be executed when the user is
        logged in
    :return:
        decorated function
    '''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' in session:
            if session['user'] in app.config['ADMIN_EMAILS']:
                return f(*args, **kwargs)
        return redirect(url_for('.index'))
        
    return decorated_function

def login_required(f):
    '''
        Allows the passed function to only be executed when the user is
        logged in
    :return:
        decorated function
    '''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' in session:
            db = client.tudev_checkout
            found_user = db.users.find_one({'email': session['user']})
            if found_user:
                return f(*args, **kwargs)
        abort(405)
        return f(*args, **kwargs)
    return decorated_function

@main.route('/submit_request', methods=['POST'])
@login_required
def submit_request():
    db = client.tudev_checkout
    data = dict(request.form)
    resp = {}
    resp['success'] = []
    resp['failed'] = []
    ordered_items = []
    for item in data:
        item_name = data[item][0]
        item_quantity = int(data[item][1])
        stored_item = db.inventory.find_one({'name': item_name})
        if(stored_item):
            if(stored_item['quantity'] >= item_quantity):
                new_quant = stored_item['quantity'] - item_quantity
                db.inventory.update({'name': item_name},
                                    {'$set': {'quantity': new_quant}})
                resp['success'].append({'name': item_name,
                                       'quantity': item_quantity})

                ordered_items.append((stored_item['item_id'], item_quantity))
            else:
                resp['failed'].append({'name': item_name,
                                       'quantity': item_quantity})

    request_id = str(uuid.uuid4())[:4]
    resp['id'] = request_id

    # if any items were checked out
    if(resp['success']):
        # send emails
        email_account = session['user']
        full_account = db.users.find_one({'email': email_account})
        if(full_account):
            user_name = full_account['name']
        else:
            user_name = None
        email_server = smtplib.SMTP(app.config['SMTP'])

        ''' add order to db '''

        '''
        order format:

        {

            id: 1234,

            name: name_of_user_who_placed_order

            email: email_of_user_who_placed_order,

            time: <TIMESTAMP_AT_TIME_OF_ORDER>,

            items: [(item_id, quantity).
            
            status: "pending" or "waiting for pickup" or "picked up" or "returned",

            overdue: boolean,

            pickup_time: <TIMESTAMP_OF_TIME_OF_PICKUP>,

            return_time: <TIMESTAMP_OF_TIME_OF_RETURN>,

            due_date: <TIMESTAMPE_OF_RETURN_DATE>

        }
        '''

        db.orders.insert({
                'id': str(uuid.uuid4())[:4],
                'name': user_name,
                'email': email_account,
                'time': datetime.utcnow(),
                'items': ordered_items,
                'status': 'pending',
                'pickup_time': None,
                'return_time': None,
                'overdue': False,
                'due_date': datetime.utcnow() + timedelta(days=14)
            })


        email_server.starttls() 
        email_server.login(app.config['EMAIL_USER'], app.config['EMAIL_PASS'])

        order_msg = email.message.Message()
        order_msg['Subject'] = 'TUDev Hardware - Item Request'
        order_msg['From'] = app.config['REQUEST_EMAIL_SEND']
        order_msg['To'] = 'TUDev Orders'
        order_msg.add_header('Content-Type', 'text/html')

        items = []
        for item in resp['success']:
            formatted_item = '''
                <li>{quantity}x {name}<hr /></li>
            '''.format(quantity=item['quantity'], name=item['name'])
            items.append(formatted_item)
        items = ''.join(items)

        safe_name = cgi.escape(user_name).encode('ascii', 'xmlcharrefreplace')
        safe_email = cgi.escape(email_account).encode('ascii',
                                                      'xmlcharrefreplace')

        email_content = '''
        <html>
        <body>
            <h1>Item Order</h1>
            <p><strong>From: </strong>{name}</p>
            <p><strong>Email: </strong>{email_account}</p>
            <p><strong>Order ID: </strong>{order_id}</p>
            <p><strong>Items ordered: </strong>
                <ul>
                    {items}
                </ul>
            </p>
        </body>
        </html>'''.format(name=safe_name, email_account=safe_email,
                          items=items, order_id=request_id)

        order_msg.set_payload(email_content)
        for account in app.config['REQUEST_EMAIL_ADMINS']:
            email_server.sendmail(app.config['REQUEST_EMAIL_SEND'],
                                  account, order_msg.as_string())

    return jsonify(resp)


@main.route('/update_order', methods=['POST'])
@admin_required
def update_order():
    '''
        updates an order's status through POST request params

        POST params
            {
                'id': string,
                'email': string,
                'new_status': string
            }
    '''

    params = request.data
    print(params)
    try:
        db = client.tudev_checkout

        # sanitize request params input so we don't insert raw data types to the
        # db, mitigates any possibility of db injection
        order_id = str(params['id'])
        order_email = str(params['email'])
        new_status = str(params['new_status'])

        order_exists = db.orders.find({'$and': [{'id': order_id},
                                                {'email': order_email}]})

        if(not(order_exists)):
            abort(404)

        print(new_status)
        '''
        db.orders.update({'$and': [{'id': order_id},
                                   {'email': order_email}]},
                         {'$set': {
                             'status': new_status
                         }})
        '''
        
    except KeyError:
        abort(400)

@main.route('/admin')
@admin_required
def admin():
    db = client.tudev_checkout
    
    inventory = db.inventory.find()
    inventory_list = []
    for item in inventory:
        formatted_item = '''
        <tr>
            <td>{item_id}</td>
            <td>{name}</td>
            <td class="hide-col">{quantity}</td>
            <td class="hide-col">{reservation_length}</td>
            <td class="hide-col">{item_category}</td>
            <td class="hide-col"><a href="{tutorials_link}">Link</a></td>
        </tr>'''.format(item_id=item['item_id'], name=item['name'],
                        quantity=item['quantity'],
                        reservation_length=item['reservation_length'],
                        item_category=item['category'],
                        tutorials_link=item['tutorials_link'])
        inventory_list.append(formatted_item)
    formatted_inventory = '\n'.join(inventory_list)

    orders = db.orders.find()
    
    order_list = []
    for order in orders:
        formatted_items = ''
        for item in order['items']:
            formatted_items += '<li>{} <strong>x</strong> {}<li>'.format(item[0], item[1])

        overdue_str = ''
        if(datetime.now() > order['due_date']):
            overdue_str = '<span class="admin-order-overdue">Overdue</span>'

        action_str= ''

        if(order['status'] == 'pending'):
            action_str = '''
                <span class="admin-order-action rfpu" name="{1}" id="{0}">
                    Ready for pickup?
                </span>'''.format(order['id'], order['email'])
        
        return_str = ''
        if(order['status'] != 'returned'):
            return_str = '''
                <span class="admin-order-return" name="{1}" id="{0}">
                  Return
                </span>'''.format(order['id'], order['email'])

        formatted_order = '''
            <div class="admin-order-view" align="left">
              <span class="admin-order-status">{5}</span>
              {6}<div class="aob"></div>{7}

              <h5 class="admin-order-view-title">
                <strong>Order ID: </strong> {0}
              </h5>
              <h5 class="admin-order-view-user">
                <strong>User: </strong> {1}
              </h5>
              <h5 class="admin-order-view-email">
                <strong>Email: </strong> {2}
              </h5>
              <h5 class="admin-order-view-items">
                <strong style="text-decoration: underline;">Items</strong>
                <ul class="admin-order-view-il">
                  {3}
                </ul>
              </h5>
              {8}<div class="aob"></div>
              <i class="admin-order-view-footer">
                Order placed on {4}
              </i>
            </div>
            '''.format(order['id'], order['name'], order['email'],
                       formatted_items,
                       moment.create(order['time']).format('dddd, MMMM Do YYYY, h:mm a'),
                       order['status'], overdue_str, action_str, return_str)
        order_list.append(formatted_order)
    order_list = ''.join(order_list)

    hackathons = db.hackathons.find()
    hackathon_list = []
    for hackathon in hackathons:
        maps_link = 'https://www.google.com/maps/search/' + \
                    hackathon['location']
        formatted_hackathon = '''
        <tr>
            <td><a href="{link}" target="_blank">{name}</a></td>
            <td class="hide-col-h">
                <a href="{location_link}" target="_blank">{location}</a>
            </td>
            <td>{date}</td>
        </tr>
        '''.format(name=hackathon['name'], location=hackathon['location'],
                   date=hackathon['date_range'], link=hackathon['link'],
                   location_link=maps_link)
        hackathon_list.append(formatted_hackathon)
    formatted_hackathons = '\n'.join(hackathon_list)

    db = client.tudev_checkout
    found_user = db.users.find_one({'email': session['user']})
    user = session['user']
    if found_user:
        if found_user['email'] == 'shetyeshail@gmail.com':
            user = 'Cuff Boy'
        else:
            user = found_user['name'].split(' ')[0]
    random_msg_index = randint(0,len(app.config['WELCOME_MSG'])-1)
    welcome_msg = app.config['WELCOME_MSG'][random_msg_index]

    return render_template('admin.html', inventory=formatted_inventory,
                           hackathons=formatted_hackathons, user=user,
                           welcome_msg=welcome_msg, orders=order_list)

@main.route('/authorize')
def authorize():
    code = request.values['code']
    oauth_url = ('https://slack.com/api/oauth.access?client_id=%s'
                 '&client_secret=%s&code=%s' % (app.config['CLIENT_ID'],
                                                app.config['CLIENT_SECRET'],
                                                code))
    oauth_verify = requests.get(oauth_url)
    
    response = json.loads(oauth_verify.text)

    print(response)

    if response['ok']:
        # set session for user
        session['user'] = response['user']['email']

        # add user to database to track how many people have signed in
        db = client.tudev_checkout
        db.users.update({'email': response['user']['email']},
                        {
                         'email': response['user']['email'],
                         'name': response['user']['name'],
                         'recent-signin': datetime.now()
                        }, upsert=True)

        if response['user']['email'] in app.config['ADMIN_EMAILS']:
            return redirect(url_for('.admin'))
        else:
            redirect(url_for('.index'))
    else:
        return jsonify({'status': 'not logged in'})

@main.route('/request_item', methods=['POST'])
@login_required
def request_item():
    data = request.form
    try:
        # convert to strings so DB injection isn't even a possibility
        name = data['name']
        email_account = data['email']
        item = data['item']
        content = data['content']

        confirm_msg = email.message.Message()
        confirm_msg['Subject'] = 'Request Item - Request Recieved'
        confirm_msg['From'] = app.config['REQUEST_EMAIL_SEND']
        confirm_msg['To'] = email_account
        confirm_msg.add_header('Content-Type', 'text/html')

        safe_name = cgi.escape(name.split(' ')[0]).encode('ascii',
                                                          'xmlcharrefreplace')
        safe_item = cgi.escape(item).encode('ascii', 'xmlcharrefreplace')

        email_content = '''
        <html>
        <body>
            <p>
            Hey {name}!
            <br>
            We recieved your request, we'll look into "{item}".
            <br>
            Happy Hacking,
            <br>
            The TUDev Team
            </p>
        </body>
        </html>'''.format(name=safe_name, item=safe_item)

        confirm_msg.set_payload(email_content)

        email_server = smtplib.SMTP(app.config['SMTP'], '587')

        email_server.starttls() 
        email_server.login(app.config['EMAIL_USER'], app.config['EMAIL_PASS'])
        # send email
        email_server.sendmail(app.config['REQUEST_EMAIL_SEND'], email_account,
                              confirm_msg.as_string())

        request_msg = email.message.Message()
        request_msg['Subject'] = 'TUDev Hardware - Item Request'
        request_msg['From'] = app.config['REQUEST_EMAIL_SEND']
        request_msg['To'] = email_account
        request_msg.add_header('Content-Type', 'text/html')

        safe_email = cgi.escape(email_account).encode('ascii',
                                                      'xmlcharrefreplace')
        safe_content = cgi.escape(content).encode('ascii', 'xmlcharrefreplace')

        email_content = '''
        <html>
        <body>
            <h1>Item Request</h1>
            <p><strong>From: </strong>{name}</p>
            <p><strong>Email: </strong>{email_account}</p>
            <p><strong>Item Requested: </strong>{item}</p>
            <p><strong>Reason for request</strong><br>{content}</p>
        </body>
        </html>'''.format(name=safe_name, email_account=safe_email, 
                          item=safe_item, content=safe_content)

        request_msg.set_payload(email_content)
        for account in app.config['REQUEST_EMAIL_ADMINS']:
            email_server.sendmail(app.config['REQUEST_EMAIL_SEND'],
                                  account, request_msg.as_string())

        return jsonify({'status': 'request sent'})

    except KeyError as e:
        abort(400)


@main.route('/inventory')
def inventory():
    return jsonify({'status': 'wip'})

@main.route('/add_hackathon', methods=['POST'])
@admin_required
def add_hackathon():
    data = request.form

    try:
        name = data['name']
        location = data['location']
        date_range = data['date']
        link = data['link']

        db = client.tudev_checkout
        safe_name = cgi.escape(name).encode('ascii', 'xmlcharrefreplace')
        safe_location = cgi.escape(location).encode('ascii',
                                                    'xmlcharrefreplace')
        safe_date = cgi.escape(date_range).encode('ascii', 'xmlcharrefreplace')
        db.hackathons.update({'name': safe_name},
                              {
                              'name': safe_name,
                              'location': safe_location,
                              'date_range': safe_date,
                              'link': link
                              }, upsert=True)
        return jsonify({'Status': 'Hackathon added/updated.'})
    except KeyError:
        abort(400)

@main.route('/remove_hackathon', methods=['POST'])
@admin_required
def remove_hackathon():
    data = request.form
    try:
        hackathon_name = data['name']
        db = client.tudev_checkout
        db.hackathons.remove({'name': hackathon_name})

        return jsonify({'status': 'hackathon removed'})
    except KeyError:
        abort(400)

@main.route('/add_item', methods=['POST'])
@admin_required
def add_tem():
    data = request.form

    try:
        name = data['name']
        quantity = int(data['quantity'])
        res_length = data['res_length']
        category = data['category']
        tutorial_link = data['item_link']
        item_id = data['item_id']

        if item_id:
            db = client.tudev_checkout

            safe_name = cgi.escape(name).encode('ascii', 'xmlcharrefreplace')
            safe_res = cgi.escape(res_length).encode('ascii',
                                                     'xmlcharrefreplace')
            safe_category = cgi.escape(category).encode('ascii',
                                                        'xmlcharrefreplace')
            safe_id = cgi.escape(item_id).encode('ascii', 'xmlcharrefreplace')
            db.inventory.update({'item_id': item_id},
                            {
                                'name': safe_name,
                                'quantity': quantity,
                                'reservation_length': safe_res,
                                'category': safe_category,
                                'tutorials_link': tutorial_link,
                                'item_id': safe_id
                            }, upsert=True)
            return jsonify({'updated': item_id})
        else:
            item_id = hashlib.sha1(bytes(os.urandom(32)))
            item_id = item_id.hexdigest()[:4]
            
            db = client.tudev_checkout

            safe_name = cgi.escape(name).encode('ascii', 'xmlcharrefreplace')
            safe_res = cgi.escape(res_length).encode('ascii',
                                                     'xmlcharrefreplace')
            safe_category = cgi.escape(category).encode('ascii',
                                                        'xmlcharrefreplace')

            db.inventory.insert({
                                'name': safe_name,
                                'quantity': quantity,
                                'reservation_length': safe_res,
                                'category': safe_category,
                                'tutorials_link': tutorial_link,
                                'item_id': item_id
                            })
            return jsonify({'inserted': item_id})
    except KeyError:
        abort(400)

    return jsonify({'status': 'done'})

@main.route('/increase_quantity', methods=['POST'])
@admin_required
def increase_quantity():
    data = request.form

    try:
        item_id = data['item_id']
        add_ons = int(data['quantity'])

        db = client.tudev_checkout

        c_item = db.inventory.find_one({'item_id': item_id})

        if c_item:
            db.inventory.update({'item_id': item_id},
                                {
                                    'name': c_item['name'],
                                    'quantity': c_item['quantity'] + add_ons,
                                    'reservation_length': c_item['reservation_length'],
                                    'category': c_item['category'],
                                    'tutorials_link': c_item['tutorials_link'],
                                    'item_id': item_id
                                })
            return jsonify({'updated': item_id})
        else:
            abort(404)
    except KeyError:
        abort(400)

@main.route('/remove_item', methods=['POST'])
@admin_required
def remove_item():
    data = request.form

    try:
        item_id = data['item_id']
        if data['quantity']:
            removals = int(data['quantity'])
        else:
            removals = 0

        if removals:
            db = client.tudev_checkout
            c_item = db.inventory.find_one({'item_id': item_id})

            if c_item:
                if c_item['quantity'] > removals:
                    db.inventory.update({'item_id': item_id},
                                        {
                                        'name': c_item['name'],
                                        'quantity': c_item['quantity'] - \
                                                    removals,
                                        'reservation_length': c_item['reservation_length'],
                                        'category': c_item['category'],
                                        'tutorials_link': c_item['tutorials_link'],
                                        'item_id': item_id
                                        })
                    return jsonify({'updated': item_id})
                else:
                    db.inventory.remove({'item_id': item_id})
                    return jsonify({'removed': item_id})
        else:
            db = client.tudev_checkout
            db.inventory.remove({'item_id': item_id})
            return jsonify({'removed': item_id})
    except KeyError:
        abort(400)

@main.route('/logout')
def logout():
    g.user = None
    session.pop('user', None)
    return redirect(url_for('.index'))    
