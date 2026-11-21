from locust import HttpUser, task, between
import random


class testingCompra(HttpUser):
    wait_time = between(0.1, 0.3)

    @task
    def comprarProductor(self):
        self.client.post("/productos/3")

    @task
    def getProductos(self):
        self.client.get("/")


# locust -f locustfile.py