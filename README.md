# Web store - a programming exercise

In class, we have talked about **monoliths** as being applications that is built and deployed as a single, unified unit — meaning that all its components are tightly integrated and run together as one program. We also explored the **maintenance challenges**:
- Harder to maintain and scale as the app grows.
- Slower deployment cycles (a small change means redeploying everything).
- Difficult for large teams to work on different parts simultaneously.
- Tightly coupled dependencies make adopting new technologies harder.

In response to these challenges, **microservices** architectures became popular A microservices architecture is a way of building software where an application is divided into many small, independent services — each responsible for a specific piece of functionality.

Each microservice:
- Runs in its **own process** (often in a container like Docker).
- Has its **own database or data store** (to reduce coupling).
- Communicates with other services using **APIs**
- Can be **developed, deployed, and scaled independently**.

## Exercise

In this exercise, you will transform a simple monolithic e-commerce application into a microservices architecture. This repository implements the monolithic web store, which consists of a web interface and a backend that implements various backend functions to support the process of ordering items through the web store.

### Web Store

Once you start the service, you can access the web store from your browser. 

![Web Store UI](docs/web_store_ui.png)

The **Service Architecture** section shows the health of the service as well as the order statistics. Below, you can select an item on the left and order it on the right-hand side. The panel below shows all the orders that have been placed. At the bottom, the **Activity Log** shows events related to service calls. Play around with it to familiarize yourself with the functionality. 

### Monolith architecture

You will find the monolith in `app/monolith/monolith.py`, which implements all the capabilities of the web store:
- **User management**: manages what users can order (and can be selected from the dropdown menu)
- **Product catalog**: manages what products are available for purchase and keeps track of their stock.
- **Order processing**: handles any orders by first checking the user and then the product before reducing the stock quantity by the purchased amount.

![Monolith](docs/monolith_architecture.svg)

These backend capabilities are exposed to the web interface via a REST API that publishes to port `5020`.

### Running the web store

To run the web store, fork this repository and clone it. Then, set up your virtual environment and install the dependencies:

```bash
python -m venv env
source env/bin/activate # env/Scripts/activate for windows
pip install -r requirements.txt
```

Now, you can run the application by running the following command:

```
python app/monolith/monolith.py
```

One you started the application, you can access the e-store at:

http://127.0.0.1:5020

### Testing the Monolith service

You can also test the service via the UI by selecting products and ordering them. Pay attention to the stock for each product and how it changes with each order. What happens when you try to order a higher quantity than what is available? What output do you see in the log at the bottom of the page?

The health status at the top of the page indicates whether your backend service is up. Stop the python process and observe how it shows in the web interface.

In addition to testing via the web interface, you can also test the REST endpoints directly using `curl` commands:

```bash
# Get all products
curl http://localhost:5020/products

# Get a specific user
curl http://localhost:5020/users/1

# Create an order
curl -X POST http://localhost:5020/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "product_id": 1, "quantity": 1}'

# Get the order
curl http://localhost:5020/orders/1
```

These are the types of requests that the UI issues also. If you see any issues in the UI, you might want to try to submit a request directly against a service for debugging.

## Part 1: Turn Monolith into Microservices

We have learned that microservices help improve modularity of an application. Do you remember why? Each  microservice focuses on a limited set of capabilities (or a single capability), which makes understanding it much simpler. It also enforces a strong interface via its REST interface and abstracts away from the implementation complexity. That means, as a consumer of the service, we only need to understand the published API but not the source code that implements the service's capabilities.

In this part of the exercise, we break down the monolithic application into individual services. You can see the application architecture below:

![Microservices](docs/microservices_architecture.svg)

Some of this conversion has already been done for you. You will find the beginning of the microservices-based application in the folder `microservices`. It already fully implements `api_gateway.py`, which takes requests from the UI and forwards it to individual services. It also provides scaffolding or `order_service.py`. It implements some of the service and provides a template of how other the other services can be implemented. Furthermore, it implements the "data store" and the `health` endpoint. You will have to implement all the parts marked as `TODO`.

You will have to finish the implementation of the `order_service.py` and fully implement `users_service.py` and `products_service.py`. We will walk through each task below.

Each service will be implemented in a separate module (i.e., file) and as a separate Flask application. As you implement the services, you should be able to copy much of the code related to each service from the monolith.

### 👥 Task 1: Create the User Service

First, you will extract the user management capability into its own service. That's an easy start.

**Instructions:**

1. Create a new file `user_service.py`
2. Copy the user-related code from the monolith
3. The service should run on port `5031`
4. Implement these endpoints:
    - `GET /users/<id>` - Get user by ID
    - `GET /health` - check that the service is up
5. Optional: implement these endpoint for more fully functional users service
    - `GET /users` - Get all users
    - `POST /users` - Create a new user

**Testing:**

You can test the correct behavior of your service by submitting a `curl` command against any of your endpoints. First, you need to run your service:

```
python user_service.py
```

The service should announce the host and port it is running on. Next, issue the `curl` commands to test the different endpoints, like so:

```bash
curl http://localhost:5001/users/1
# Should return: {"id": 1, "name": "Alice", "email": "alice@example.com"}
```

This is referred to as *component testing*. We will talk about that more later.

### 🛍 Task 2: Create the Product Service

Next, you will extract the product catalog into its own service. It should be similarly straight-forward.

**Instructions:**

1. Create `product_service.py` running on port `5032`
2. Implement endpoints:
    - `GET /` - List all products
    - `GET /<id>` - Get product by ID
    - `PUT /<id>/stock` - Update stock (for order service to call)
    - `GET /health` - check that the service is up

**Hint - creating the new decrement endpoint**:

```python
@app.route('/<int:product_id>/stock', methods=['PUT'])
def update_product_stock(product_id):
	# Read stock quantity from PUT body
	data = request.json
	if data is None:
		return jsonify({"error": "Invalid data"}), 400
	stock = data.get('stock')
	
	# Get product ID from URL parameter
	product = products.get(product_id)
	...
```


**Testing:**

Again, start your service and run a `curl` against each endpoint like so:

```bash
curl -X PUT -H "Content-Type: application/json" -d '{"stock": 30}' http://localhost:5032/stock
# Should return: {"id": 1, "name": "Laptop", "price": 999.99, "stock": 30}
```

If everything looks good, you have completed testing that service.

### 🛒 Task 3: Update Order Service

Let's take a look at a more complex service. The `order_service.py` has already been created. Address all the places marked `TODO` in the code. This service is slightly different from the other two as it has to call the other services by making REST calls using the `requests` library.

**Instructions:**

1. Implement endpoint:
	- `PUT /` - add an order
2. When creating an order, the service should:
    - Call User Service to validate the user exists
    - Call Product Service to check product availability
    - Call Product Service to decrement stock
3. Handle errors when services are unavailable

**Hint - Making HTTP calls (to product and user services):**

```python
import requests

# Call user service
response = requests.get(f'http://127.0.0.1:5031/{user_id}')
if response.status_code == 404:
    return jsonify({"error": "User not found"}), 404
user_data = response.json()
```

**Testing**:

Again, run the service and issue `curl` commands to the different endpoints. This service will only be able to respond to the `PUT` endpoint if both the user and and product service are running also since it will try to fetch information from both services. Run each of the services in a different terminal. Then run the `curl` command against the `PUT` endpoint. With this, you are performing *integration testing*. We will discuss that in class also. 

### 🛒 Task 4: System test

Now that you have tested all the services and the communication between them, you can go test out whether the UI works. Start up all services, including the `api_gateway.py`. The gateway service also hosts the UI. You should be able to go to:

http://127.0.0.1:5030

Now, follow the same procedures to test out the UI as you did initially. If anything doesn't work, take a look at the network tab of the developer tools in your browser. Also study the output of the different services.



## Part 2: Advanced Tasks

You have successfully converted the monolith into a microservices architecture? Well done! If you are up for somewhat more challenging tasks, I invite you to take a stab at any or both of the tasks below. They are extending the microservices architecture with sensible capabilities that you would see in more of a production-ready environment.

### 💾 Task 5: Add Database per Service

The basic application holds all data in memory and is hard-coded. That is of course not ideal and not something you would want to do in a real application. Create a database for one or all three of the services to hold the data that is currently in memory. This will retain information across service restarts!

**Instructions:**

1. Set up SQLite databases for each service
2. Migrate in-memory data to persistent storage
3. Update service to read from and write to the database

**Hint - create the table schema (for products):**

```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL
    )
''')
```

### 🔍 Task 6: Implement Service Discovery

In the current implementation, all the services need to know where other services are dpeloyed in order to connect to them. For instance, the `order_service.py` needs to know the host and port of the `product_service.py` and `user_service.py`. That leads to maintenance challenges and makes changes less reliable.

To address that problem, implement a separate service that acts as service registry. Services would register with that registry as producers and consuming services would use the registry to obtain the URL of the service they want to connect to. For instance, `order_service.py` would connect to `service_registry.py` to obtain the URL for `product_service.py`. This makes the entire system more flexible.

**Instructions:**

1. Create a simple service registry (using the template below).
2. Update other services register themselves on startup.
3. Update other services to fetch the URL of the service before they connect.
4. Remove any hard-coded service URLs.
5. Start it all up and test it.

You may want to do this incrementally. For instance, start with the `order_service.py` and `product_service.py` and iron out any issues before expanding to other services.

**Starter code for registry:**

```python
# service_registry.py
from flask import Flask, jsonify, request

app = Flask(__name__)
services = {}  # {service_name: url}

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    service_name = data.get('name')
    service_url = data.get('url')
    services[service_name] = service_url
    return jsonify({"status": "registered"})

@app.route('/discover/<service_name>', methods=['GET'])
def discover(service_name):
    url = services.get(service_name)
    if url:
        return jsonify({"url": url})
    return jsonify({"error": "Service not found"}), 404

if __name__ == '__main__':
    app.run(port=5100, debug=True)
```

### Running the microservices

Start each command in a separate terminal from the repository root, in this order:

```powershell
python -m microservices.service_registry
python -m microservices.user_service
python -m microservices.product_service
python -m microservices.order_service
python -m microservices.api_gateway
```

The services register with the registry at `http://127.0.0.1:5100` when they start. Start the registry first; if it is unavailable, the service reports the registration error instead of starting unregistered. The gateway and order service discover service URLs from the registry. Set `SERVICE_REGISTRY_URL` to use a registry at a different address; `USERS_SERVICE_URL`, `PRODUCTS_SERVICE_URL`, and `ORDERS_SERVICE_URL` control the URLs each service advertises.

Each data-owning service creates its own SQLite database in the `microservices` directory on startup (`users.db`, `products.db`, and `orders.db`). User and product databases are seeded with the initial sample data only when their IDs are absent, so subsequent changes persist across restarts. Database paths can be overridden with `USERS_DATABASE`, `PRODUCTS_DATABASE`, and `ORDERS_DATABASE`.