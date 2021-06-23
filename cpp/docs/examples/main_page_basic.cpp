#include "sina/sina.hpp"

int main (void) {
    // Create a new document
    sina::Document document;

    // Create a run of "My Sim Code" version "1.2.3", which was run by "jdoe".
    // The run has an ID of "run1", which has to be unique to this file.
    // There can be different types of records, so we allocate them dynamically.
    sina::ID run1ID{"run1", sina::IDType::Local};
    std::unique_ptr<sina::Record> run1{new sina::Run{run1ID, "My Sim Code", "1.2.3", "jdoe"}};

    // Add the run to the document
    document.add(std::move(run1));

    // Create and add another run
    sina::ID run2ID{"run2", sina::IDType::Local};
    // std::unique_ptr is used with Record entries to avoid object slicing, as Records can be subclassed
    std::unique_ptr<sina::Record> run2{new sina::Run{run2ID, "My Sim Code", "1.2.3", "jdoe"}};
    document.add(std::move(run2));

    // Add a relationship between the runs showing that 1 came before 2
    sina::Relationship oneBeforeTwo{run1ID, "comes before", run2ID};
    document.add(oneBeforeTwo);

    // Save the document directly to a file.
    saveDocument(document, "MySinaData.json");

    // Print the contents to the screen
    std::cout << document.toJson() << std::endl;
}

