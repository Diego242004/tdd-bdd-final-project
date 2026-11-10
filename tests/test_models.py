# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test cases for the Product model."""

import logging
import os
import unittest
from decimal import Decimal

from service import app
from service.models import Category, DataValidationError, Product, db
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test cases for the Product model."""

    @classmethod
    def setUpClass(cls):
        """Configure the app and initialize the database."""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Close the database session."""
        db.session.close()

    def setUp(self):
        """Clear the product table before each test."""
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        """Remove the database session after each test."""
        db.session.remove()

    def test_create_a_product(self):
        """It should create a Product object."""
        product = Product(
            name="Fedora",
            description="A red hat",
            price=Decimal("12.50"),
            available=True,
            category=Category.CLOTHS,
        )

        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertIsNone(product.id)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.price, Decimal("12.50"))
        self.assertTrue(product.available)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should add a Product to the database."""
        self.assertEqual(Product.all(), [])

        product = ProductFactory()
        product.id = None
        product.create()

        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)

        saved_product = products[0]
        self.assertEqual(saved_product.id, product.id)
        self.assertEqual(saved_product.name, product.name)
        self.assertEqual(saved_product.description, product.description)
        self.assertEqual(saved_product.price, product.price)
        self.assertEqual(saved_product.available, product.available)
        self.assertEqual(saved_product.category, product.category)

    def test_read_a_product(self):
        """It should read a Product by ID."""
        product = ProductFactory()
        app.logger.info("Product to read: %s", product)

        product.id = None
        product.create()
        product_id = product.id
        self.assertIsNotNone(product_id)

        expected = product.serialize()
        db.session.remove()

        found_product = Product.find(product_id)

        self.assertIsNotNone(found_product)
        self.assertEqual(found_product.serialize(), expected)

    def test_update_a_product(self):
        """It should update a Product without changing its ID."""
        product = ProductFactory(description="Original description")
        app.logger.info("Product before creation: %s", product)

        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        app.logger.info("Product after creation: %s", product.serialize())

        original_id = product.id
        product.description = "testing"
        product.update()

        self.assertEqual(product.id, original_id)
        self.assertEqual(product.description, "testing")

        db.session.remove()
        products = Product.all()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].id, original_id)
        self.assertEqual(products[0].description, "testing")

    def test_delete_a_product(self):
        """It should delete a Product from the database."""
        product = ProductFactory()
        product.create()
        self.assertEqual(len(Product.all()), 1)

        product.delete()

        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        """It should list all Products in the database."""
        products = Product.all()
        self.assertEqual(products, [])

        for _ in range(5):
            product = ProductFactory()
            product.create()

        products = Product.all()
        self.assertEqual(len(products), 5)

    def test_find_by_name(self):
        """It should find Products by name."""
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()

        name = products[0].name
        expected_count = sum(1 for product in products if product.name == name)

        found = Product.find_by_name(name)

        self.assertEqual(found.count(), expected_count)
        for product in found:
            self.assertEqual(product.name, name)

    def test_find_by_availability(self):
        """It should find Products by availability."""
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()

        available = products[0].available
        expected_count = sum(
            1 for product in products if product.available == available
        )

        found = Product.find_by_availability(available)

        self.assertEqual(found.count(), expected_count)
        for product in found:
            self.assertEqual(product.available, available)

    def test_find_by_category(self):
        """It should find Products by category."""
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()

        category = products[0].category
        expected_count = sum(
            1 for product in products if product.category == category
        )

        found = Product.find_by_category(category)

        self.assertEqual(found.count(), expected_count)
        for product in found:
            self.assertEqual(product.category, category)

    def test_find_by_price(self):
        """It should find Products by decimal and string prices."""
        product = ProductFactory(price=Decimal("12.50"))
        product.create()
        ProductFactory(price=Decimal("20.00")).create()

        for price in (Decimal("12.50"), "12.50"):
            with self.subTest(price=price):
                found = Product.find_by_price(price).all()
                self.assertEqual([match.id for match in found], [product.id])

    def test_deserialize_invalid_product_fields(self):
        """It should reject invalid availability and category values."""
        data = ProductFactory().serialize()
        invalid_fields = {"available": "true", "category": "INVALID"}

        for field, value in invalid_fields.items():
            with self.subTest(field=field):
                with self.assertRaises(DataValidationError):
                    Product().deserialize(dict(data, **{field: value}))
