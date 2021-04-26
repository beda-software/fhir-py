## 1.2.1
* Fix delete operation. Always use `Accept` header instead of `_format` #71

## 1.2.0
* Add more tests
* Fix fetch_all() – use "next" value #47
* Fix to_resource, tests and readme – replace "id" search param by "_id" #55
* Fix for absolute url's in "next" link (fetch_all/searchset iterator). Related to #47
* Add .refresh() method to resource #48
* Add .update() and save(fields=[...]) – allow to PATCH resource #31
* Update resource on save with returned response #58
* Add client.execute() and resource.execute() methods for executing FHIR operations #60

## 1.1.0
* Remove schemas and resource key validation #33
* Add support for operation $validate for resource – method is_valid(raise_exception=True) #30
* Remove caching #36
* Support search params with method .get() #29
* Parameter 'id' of method .get() is now deprecated (use .search(id='...').get() instead)
* Make searchset iterating lazy #35
* Add :iterate modifier for include and revinclude
* Support wild card include and revinclude
* Support chained params #43

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
