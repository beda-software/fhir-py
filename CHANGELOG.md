## Development
* Remove schemas and resource key validation
* Add support for operation $validate for resource – method is_valid(raise_exception=True)

## 1.0.0
This version breaks backward compatibility, but the main class structure and set of methods remain the same.
* Rework library and make separate sync (based on requests) and async (based on aiohttp client) versions
* Fix bug where we feed bytes instead of str to json.loads on success response
* Add fhir-4.0.0 schema
* Update readme, add more examples
* Add searchset methods .revinclude() and .fetch_raw()
* Add support for using get_by_path on any nested attribute of resource
* Add support for snake case search parameters
* Add support for quantifiers in .search
* Transform boolean value into 'true' or 'false' instead of 'True' or 'False' in .search()
* Add support for python date/datetime as a search value in .search()
* Transform FHIRResource/FHIRReference in search lookups

## 0.2.0
* Fix requirements

## 0.1.2 
* Fix page method (use page instead of _page query param)

## 0.1.1
* Initial public release (based on aidbox-py)
