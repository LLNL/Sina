// Take a path to a JSON file and a target path, ingest the JSON, and write it to the target.
// Used to test JSON writing capabilities and coherence with Sina Python
#include <string>
#include <fstream>
#include <streambuf>

#include "sina/sina.hpp"


int main(int argc, char** argv){
    if(argc<3){
        std::cout << "Usage: <input file> <output path>";
        return 1;
    }
    std::string input_path = argv[1];
    std::string output_path = argv[2];
    std::ifstream json_file(input_path);
    std::stringstream json_buffer;
    json_buffer << json_file.rdbuf();
    sina::Document myDocument = sina::Document(json_buffer.str(), sina::createRecordLoaderWithAllKnownTypes());
    saveDocument(myDocument, output_path);
    return 0;
}
