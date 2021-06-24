#include "sina/sina.hpp"

#include <utility>
#include <memory>

namespace {

//! [create record]
void createRecord() {
    sina::ID id{"some_record_id", sina::IDType::Local};
    std::unique_ptr<sina::Record> record{new sina::Record{id, "my_record_type"}};

    // Add the record to a document
    sina::Document doc;
    doc.add(std::move(record));
}
//! [create record]

//! [create run]
void createRun() {
    sina::ID id{"some_run_id", sina::IDType::Local};
    std::unique_ptr<sina::Record> run{new sina::Run{id, "My Sim Code", "1.2.3", "jdoe"}};

    // Add the record to a document
    sina::Document doc;
    doc.add(std::move(run));
}
//! [create run]

//! [saving]
//! [saving]

//! [adding data]
void addData(sina::Record &record) {
    // Add a scalar named "my_scalar" with the value 123.456
    record.add("my_scalar", sina::Datum{123.456});

    // Add a string named "my_string" with the value "abc"
    record.add("my_string", sina::Datum{"abc"});

    // Add a list of scalars named "my_scalar_list"
    std::vector<double> scalarList = {1.2, -3.4, 5.6};
    record.add("my_scalar_list", sina::Datum{scalarList});

    // Add a list of strings named "my_string_list"
    std::vector<std::string> stringList = {"hi", "hello", "howdy"};
    record.add("my_string_list", sina::Datum{stringList});
}
//! [adding data]

//! [curve sets]
void addCurveSets(sina::Record &record) {
    sina::CurveSet timePlots{"time_plots"};

    // Add the independent variable
    timePlots.addIndependentCurve(
        sina::Curve{"time", {0.0, 0.1, 0.25, 0.3}});

    // Add some dependent variables.
    // The length of each must be the same as the length of the independent.
    timePlots.addDependentCurve(
        sina::Curve{"temperature", {300.0, 310.0, 350.0, 400.0}});

    timePlots.addDependentCurve(
        sina::Curve{"energy", {0.0, 10.0, 20.0, 30.0}});

    // Associate the curve sets with the record
    record.add(timePlots);
}

//! [curve sets]

//! [relationships]
void associateRunToStudy(sina::Document &doc, sina::Record const &uqStudy, sina::Record const &run) {
    doc.add(sina::Relationship{uqStudy.getId(), "contains", run.getId()});
}
//! [relationships]

} // unnamed namespace

// Forward declaration to avoid compiler errors
namespace foo {
void collectData(sina::DataHolder &fooData);
}

namespace bar {
void gatherData(sina::DataHolder &barData);
}

//! [library data foo]
namespace foo {
void collectData(sina::DataHolder &fooData) {
    fooData.add("temperature", sina::Datum{500});
    fooData.add("energy", sina::Datum{1.2e10});
}
}
//! [library data foo]

//! [library data bar]
namespace bar {
void gatherData(sina::DataHolder &barData) {
    barData.add("temperature", sina::Datum{400});
    barData.add("mass", sina::Datum{15});
}
}
//! [library data bar]

namespace {

//! [library data host]
void gatherAllData(sina::Record &record) {
   auto fooData = record.addLibraryData("foo");
   auto barData = record.addLibraryData("bar");

   foo::collectData(*fooData);
   bar::gatherData(*barData);

   record.add("temperature", sina::Datum{450});
}
//! [library data host]

//! [io write]
void save(sina::Document const &doc) {
    sina::saveDocument(doc, "my_output.json");
}
//! [io write]

//! [io read]
void load() {
    sina::Document doc = sina::loadDocument("my_output.json");
}
//! [io read]

//! [user defined]
void addUserDefined(sina::Record &record) {
    conduit::Node &userDefined = record.getUserDefinedContent();
    userDefined["var_1"] = "a";
    userDefined["var_2"] = "b";

    conduit::Node subNode;
    subNode["sub_1"] = 10;
    subNode["sub_2"] = 20;
    userDefined["sub_structure"] = subNode;
}
//! [user defined]

}

int main() {
    // Call everything to keep the compiler from complaining about unused functions
    sina::Record run{sina::ID{"my_record", sina::IDType::Global}, "my_record_type"};
    sina::Record study{sina::ID{"my_run", sina::IDType::Global}, "UQ study"};
    sina::Document doc;
    addData(run);
    createRecord();
    createRun();
    associateRunToStudy(doc, study, run);
    gatherAllData(run);
    addCurveSets(run);
    addUserDefined(run);
    save(doc);
    load();
}
