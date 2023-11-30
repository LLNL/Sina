"""Test the SQL portion of the DAO structure."""

# pylint: disable=no-value-for-parameter, too-few-public-methods, import-error,no-self-use

import unittest
import os

import random
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Float, Integer, ForeignKey, String, Column, create_engine, and_
from sqlalchemy.ext.hybrid import hybrid_method
from sina.model import Record
from sina.datastores.sql_schema import ScalarData
# IMPORTANT TO USE THIS Base since the Record table is already in there
from sina.datastores.sql_schema import Base
import sina

# Accessing "private" methods is necessary for testing them.
# pylint: disable=protected-access

# Our test classes, as with the other tests, have public methods *as* tests.
# pylint: disable=too-many-public-methods


class TestORM(unittest.TestCase):
    """Unit tests for the model utility methods."""

    def setUp(self):
        self.uri = f"{random.randint(0, 100000)}.sqlite"
        self.store = sina.connect(self.uri)
        # create dummy records
        for i in range(20):
            rec = Record(f"{i}", f"sina{i}")
            rec.add_data("simulation_name", f"sim_{i}")
            rec.add_data("status", i % 2 == 0)
            rec.add_data("score", i + 0.5)
            if i % 2:
                rec.add_data("odd", 1)
            else:
                rec.add_data("even", 1)
            self.store.records.insert(rec)
        self.engine = create_engine(f"sqlite:///{self.uri}")
        self.session = sessionmaker(bind=self.engine)()

    def tearDown(self):
        os.remove(self.uri)

    def test_create_orm_mapping_from_col_names(self):
        """test orm mapping from list of columns"""
        Simulation = sina.utils.make_sina_sqlalchemy_class(
            self.store, ["simulation_name", "status", "score"])
        results = list(self.session.query(Simulation))
        self.assertEqual(len(results), 20)
        count_odd = 0
        count_even = 0
        for result in results:
            self.assertTrue(hasattr(result, "score"))
            self.assertTrue(hasattr(result, "status"))
            self.assertTrue(hasattr(result, "simulation_name"))
            try:
                _ = result.odd
                count_odd += 1
            except (KeyError, AttributeError):
                pass
            try:
                _ = result.even
                count_even += 1
            except (KeyError, AttributeError):
                pass
        self.assertEqual(count_odd, 0)
        self.assertEqual(count_even, 0)  # We didn't pass even has a col so it should be 0

    def test_create_orm_mapping_sina_record(self):
        """test orm mapping from sina record"""
        rec = self.store.records.get("0")
        Simulation = sina.utils.make_sina_sqlalchemy_class(self.store, rec)
        results = list(self.session.query(Simulation))
        self.assertEqual(len(results), 20)
        count_odd = 0
        count_even = 0
        for result in results:
            self.assertTrue(hasattr(result, "score"))
            self.assertTrue(hasattr(result, "status"))
            self.assertTrue(hasattr(result, "simulation_name"))
            try:
                _ = result.odd
                count_odd += 1
            except (KeyError, AttributeError):
                pass
            try:
                _ = result.even
                count_even += 1
            except (KeyError, AttributeError):
                pass
        self.assertEqual(count_odd, 0)
        self.assertEqual(count_even, 10)

    def test_orm_filter_funcs(self):
        """test orm filters on mapped Sina record"""
        Simulation = sina.utils.make_sina_sqlalchemy_class(
            self.store, ["simulation_name", "status", "score"])
        results = self.session.query(Simulation).join(ScalarData).filter(
            Simulation.greater_column_name("score", 5.)).all()
        self.assertEqual(len(results), 15)
        results = self.session.query(Simulation).filter(
            Simulation.like_column_name("simulation_name", "sim_3")).all()
        self.assertEqual(len(results), 1)
        results = self.session.query(Simulation).filter(
            Simulation.like_column_name("simulation_name", "sim_1%")).all()
        self.assertEqual(len(results), 11)
        results = self.session.query(Simulation).filter(
            Simulation.like_column_name("status", True)).all()
        self.assertEqual(len(results), 10)

        class SuperSim(Simulation):
            """Class adding between filter to Simulation class"""
            def get_record(self):
                """Get the record"""
                return self.__sina_records.get(self.id)

            @hybrid_method
            def inbetween_column_name(self, column_name, value1, value2):
                """Returns records whose column `column_name` in between value1 and value2"""
                return and_(and_(ScalarData.name == column_name,
                                 ScalarData.value > value1), ScalarData.value < value2)
        results = self.session.query(SuperSim).join(ScalarData).filter(
            SuperSim.inbetween_column_name("score", 5., 8.)).all()
        self.assertEqual(len(results), 3)

    def test_mix_orm_sina(self):
        """test mixing sina records and regular orm model"""
        Simulation = sina.utils.make_sina_sqlalchemy_class(
            self.store, ["simulation_name", "status", "score"])

        class Model(Base):
            """some generic Model"""
            __tablename__ = "__models__"
            id = Column(Integer, primary_key=True)  # Regular primary key
            # Sina's Record primary key is a String
            simulation_id = Column(String, ForeignKey("Record.id"))
            quality = Column(Float)

            # Define the relationship with Sina table
            simulation = relationship("Record")

        Base.metadata.create_all(self.engine)

        model1 = Model(simulation_id="9", quality=13.2)  # sim score less than 10
        # sim score greater than 10 but value less than 5
        model2 = Model(simulation_id="11", quality=4.8)
        # simm core greater 10 and value greater 5
        model3 = Model(simulation_id="14", quality=61.9)
        model4 = Model(simulation_id="4", quality=4.1)  # Add a model with score > 10 and value < 5

        self.session.add_all([model1, model2, model3, model4])

        query = self.session.query(Simulation).join(Model).filter(
            Model.quality < 5).join(ScalarData).filter(
                Simulation.greater_column_name(
                    "score", 10.))
        results = query.all()

        self.assertEqual(len(results), 1)

        result = results[0]
        self.assertEqual(result.simulation_name, "sim_11")

        query = self.session.query(Model).filter(
            Model.quality < 5).join(Simulation).join(ScalarData).filter(
                Simulation.greater_column_name(
                    "score", 10.))

        results = query.all()

        self.assertEqual(len(results), 1)

        result = results[0]
        self.assertEqual(result.quality, 4.8)
