
#include "sina/Document.hpp"
#include "sina/Record.hpp"
#include "sina/Run.hpp"
#include "sina/sina.hpp"

extern "C" char* Get_File_Extension(char *);
extern "C" void create_document_and_run_(char *);
extern "C" sina::Record *Sina_Get_Run();
extern "C" void sina_add_file_to_record_(char *);
extern "C" void sina_add_file_with_mimetype_to_record_(char *, char *);
extern "C" void write_sina_document_(char *);
extern "C" void sina_add_long_(char *, long long int *, char *, char *);
extern "C" void sina_add_int_(char *, int *, char *, char *);
extern "C" void sina_add_float_(char *, float *, char *, char *);
extern "C" void sina_add_double_(char *, double *, char *, char *);
extern "C" void sina_add_logical_(char *, bool *, char *, char *);
extern "C" void sina_add_string_(char *, char *, char *, char *);
extern "C" void sina_add_curveset_(char *);
extern "C" void sina_add_curve_double_(char *, char *, double *, int *, bool *);
extern "C" void sina_add_curve_float_(char *, char *, float *, int *, bool *);
extern "C" void sina_add_curve_int_(char *, char *, int *, int *, bool *);
extern "C" void sina_add_curve_long_(char *, char *, long long int *, int *, bool *);

