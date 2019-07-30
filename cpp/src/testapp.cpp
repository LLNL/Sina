#include "adiak.hpp"
#include <vector>
#include <set>
#include "sina/AdiakWriter.hpp"
#include "sina/Document.hpp"
#include "sina/Record.hpp"

#include <time.h>
#include <sys/time.h>


extern "C" {
  #include "adiak_tool.h"
  #if defined(USE_MPI)
    #include <mpi.h>
  #endif
}


using namespace std;

int main(int argc, char *argv[])
{
   sina::Document doc;
   sina::ID id{"test_run", sina::IDType::Local}; 
   std::unique_ptr<sina::Record> run{new sina::Run{id, "testappcxx", "1.0"}};
   doc.add(std::move(run));
   void *record_ptr = static_cast<void *>(doc.getRecords()[0].get());
   adiak_register_cb(1, adiak_category_all, sina::adiakSinaCallback, 0, record_ptr);
   bool result;
#if defined(USE_MPI)
   MPI_Comm world = MPI_COMM_WORLD;
#endif
   struct timeval start, end;

   gettimeofday(&start, NULL);
#if defined(USE_MPI)
   MPI_Init(&argc, &argv);
   adiak::init(&world);
#else
   adiak::init();
#endif

   vector<double> grid;
   grid.push_back(4.5);
   grid.push_back(1.18);
   grid.push_back(0.24);
   grid.push_back(8.92);

   set<string> names;
   names.insert("matt");
   names.insert("david");
   names.insert("greg");

   vector<tuple<string, double, double> > points;

   points.push_back(make_tuple("first", 1.0, 1.0));
   points.push_back(make_tuple("second", 2.0, 4.0));
   points.push_back(make_tuple("third", 3.0, 9.0));

   vector<string> ap_a;
   ap_a.push_back("first");
   ap_a.push_back("second");
   ap_a.push_back("third");
   vector<double> ap_b;
   ap_b.push_back(1.0);
   ap_b.push_back(2.0);
   ap_b.push_back(3.0);
   vector<double> ap_c;
   ap_c.push_back(1.0);
   ap_c.push_back(4.0);
   ap_c.push_back(9.0);
   tuple<vector<string>, vector<double>, vector<double> > antipoints = make_tuple(ap_a, ap_b, ap_c);
   const tuple<vector<string>, vector<double>, vector<double> > &antipoints_r = antipoints;

   //These first three are forms Sina doesn't deal with
   //result = adiak::value("points", points);
   //if (!result) printf("return: %d\n\n", result);

   //result = adiak::value("antipoints", antipoints_r);
   //if (!result) printf("return: %d\n\n", result);
   
   //result = adiak::value("antipoints_r", antipoints_r);
   //if (!result) printf("return: %d\n\n", result);

   result = adiak::value("str", std::string("s"));
   if (!result) printf("return: %d\n\n", result);
 
   result = adiak::value("compiler", adiak::version("gcc@8.1.0"));
   if (!result) printf("return: %d\n\n", result);

   result = adiak::value("mydouble", (double) 3.14);
   if (!result) printf("return: %d\n\n", result);

   result = adiak::value("gridvalues", grid);
   if (!result) printf("return: %d\n\n", result);

   result = adiak::value("problemsize", 14000);
   if (!result) printf("return: %d\n\n", result);

   result = adiak::value("allnames", names);
   if (!result) printf("return: %d\n\n", result);

   result = adiak::value("githash", adiak::catstring("a0c93767478f23602c2eb317f641b091c52cf374"));
   if (!result) printf("return: %d\n\n", result);
   
   result = adiak::value("birthday", adiak::date(286551000));
   if (!result) printf("return: %d\n\n", result);

   result = adiak::value("nullpath", adiak::path("/dev/null"));
   if (!result) printf("return: %d\n\n", result);

   result = adiak::user();
   if (!result) printf("return: %d\n\n", result);
   
   result = adiak::uid();
   if (!result) printf("return: %d\n\n", result);

   result = adiak::launchdate();
   if (!result) printf("return: %d\n\n", result);

   result = adiak::executable();
   if (!result) printf("return: %d\n\n", result);

   result = adiak::executablepath();
   if (!result) printf("return: %d\n\n", result);

   //might break here
   result = adiak::libraries();
   if (!result) printf("return: %d\n\n", result);
   
   // might break here
   result = adiak::cmdline();
   if (!result) printf("return: %d\n\n", result);

   result = adiak::hostname();
   if (!result) printf("return: %d\n\n", result);

   result = adiak::clustername();
   if (!result) printf("return: %d\n\n", result);
 
   result = adiak::walltime();
   if (!result) printf("return: %d\n\n", result);

   result = adiak::cputime();
   if (!result) printf("return: %d\n\n", result);
 
   result = adiak::systime();
   if (!result) printf("return: %d\n\n", result);   

   result = adiak::jobsize();
   if (!result) printf("return: %d\n\n", result);

   printf("Should be over here");
   //result = adiak::hostlist();
   //if (!result) printf("return: %d\n\n", result);

   //gettimeofday(&end, NULL);
   //result = adiak::value("computetime", &start, &end);
   //if (!result) printf("return: %d\n\n", result);
   
   array<float, 3> floatar;
   floatar[0] = 0.01f;
   floatar[1] = 0.02f;
   floatar[2] = 0.03f;
   //result = adiak::value("floats", floatar);
   if (!result) printf("return: %d\n\n", result);
   //sina::flushRecord("test.json");
   std::cout << doc.toJson().dump(4) << std::endl; 
   adiak::fini();
#if defined(USE_MPI)   
   MPI_Finalize();
#endif
   return 0;
}
