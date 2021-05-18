#ifndef SINA_DATAHOLDER_HPP
#define SINA_DATAHOLDER_HPP

#include <string>
#include <memory>
#include <unordered_map>

#include "conduit.hpp"

#include "sina/Datum.hpp"
#include "sina/CurveSet.hpp"

namespace sina {

/**
 * A DataHolder is a basic container for certain types of information.
 *
 * DataHolders contain curves, libraries, and/or data (\see Datum), and represent
 * all the information a library can have associated with it. Records expand
 * on DataHolders to contain additional info.
 *
 * \see Record
 * \see LibraryData
 */
class DataHolder {
public:
    using DatumMap = std::unordered_map<std::string, Datum>;
    using CurveSetMap = std::unordered_map<std::string, CurveSet>;
    using LibraryDatumMap = std::unordered_map<std::string, std::shared_ptr<DataHolder>>;

    /**
     * Construct an empty DataHolder.
     */
    DataHolder(){}

    /**
     * Construct a DataHolder from its conduit Node representation.
     *
     * @param asNode the DataHolder as a Node
     */
    explicit DataHolder(conduit::Node const &asNode);

    /**
     * Get the DataHolder's data.
     *
     * @return the DataHolder's data
     */
    DatumMap const &getData() const noexcept {
        return data;
    }

    /**
     * Add a Datum to this DataHolder.
     *
     * @param name the key for the Datum to add
     * @param datum the Datum to add
     */
    void add(std::string name, Datum datum);

    /**
     * Add a CurveSet to this DataHolder.
     *
     * @param curveSet the CurveSet to add
     */
    void add(CurveSet curveSet);

    /**
     * Get the curve sets associated with this DataHolder.
     *
     * @return the dataholder's curve sets
     */
    CurveSetMap const &getCurveSets() const noexcept {
        return curveSets;
    }

    // TODO: should there be an add() for a completed LibraryData?

    /**
     * Add a new library to this DataHolder.
     *
     * @return a pointer to a new DataHolder for a library
     * of the given name.
     */
    std::shared_ptr<DataHolder> add_library_data(std::string const &name);

    /**
     * Get the library data associated with this DataHolder.
     *
     * @return the dataholder's library data
     */
    LibraryDatumMap const &getLibraryData() const noexcept {
        return libraryData;
    }

    /**
     * Convert this DataHolder to its conduit Node representation.
     *
     * @return the Node representation of this DataHolder.
     */
    conduit::Node toNode() const;


private:
    CurveSetMap curveSets;
    DatumMap data;
    LibraryDatumMap libraryData;
};

}

#endif //SINA_DATAHOLDER_HPP
