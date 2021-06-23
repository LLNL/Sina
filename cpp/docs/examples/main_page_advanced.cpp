#include <vector>
#include <cstdlib>
#include <iostream>
#include <string>

#include "sina/sina.hpp"

int main() {
    // Define some names for Data
    std::vector<std::string> datumNames{"length", "width", "height"};
    // Create the Document we'll be adding to
    sina::Document exampleDocument;

    // Create the Record (type: task) that will "contain" the Runs
    sina::ID exampleTaskId{"example_task", sina::IDType::Global};
    std::unique_ptr<sina::Record> exampleTask{new sina::Record{exampleTaskId, "task"}};

    // Loop for creating Runs and Relationships
    for(int i = 0; i < 10; i++) {
        // Create the Run ID and the Run itself
        sina::ID exampleRunId{"example_run_"+std::to_string(i), sina::IDType::Local};
        std::unique_ptr<sina::Record> exampleRun{new sina::Run{exampleRunId, "example_app", "1.2", "jdoe"}};

        // Add a few Data to the Run
        for(auto &datumName : datumNames){
            double randomVal = std::rand();
            exampleRun->add(datumName, sina::Datum{randomVal});
        }   
        // Add a File to the Run
        sina::File exampleFile{"/foo/bar/summary_"+std::to_string(i)+".txt"};
        exampleFile.setMimeType("text/plain");
        exampleRun->add(exampleFile);

        // Make a Relationship linking the Run and its containing Record
        sina::Relationship exampleRelationship{exampleTaskId, "contains", exampleRunId};

        // Add the Relationship and Run to the Document
        exampleDocument.add(exampleRelationship);
        exampleDocument.add(std::move(exampleRun));
    }   

    // Add the Task to the Document
    exampleDocument.add(std::move(exampleTask));

    // Print the JSON
    std::cout << exampleDocument.toJson() << std::endl;
}
