#include "sina/sina.hpp"

int main (void) {
    // Create a new document
    sina::Document document;

    // Create a run of "My Sim Code" version "1.2.3", which was run by "jdoe".
    // The run has an ID of "run1", which has to be unique to this file.
    sina::ID runID{"run1", sina::IDType::Local};
    std::unique_ptr<sina::Record> run{
        new sina::Run{runID, "My Sim Code", "1.2.3", "jdoe"}};

    // Add the run to the document
    document.add(std::move(run));

    // Save the document directly to a file.
    saveDocument(document, "MySinaData.json");
}

