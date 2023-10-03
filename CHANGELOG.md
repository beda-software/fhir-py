## 1.4.2
* Conditional delete @pavlushkin

## 1.4.1
* Implement conditional operations #112:
  * ! BREAKING CHANGE: `resource.update(partial_resource)` is replaced with `resource.patch(partial_resource)`, `resource.update(params)` works as conditional update and accepts `search_params` instead of partial resource
  * Migration guide:
    * `resource.update(active=True)` -> `resource.patch(active=True)`
* Fix get resource by id: `reference.to_resource()` is `GET /<resource_type>/<id>` instead of `GET /<resource_type>?_id=<id>` #111
* Bump aiohttp from 3.7.4 to 3.8.5 by @dependabot in #105
* Bump certifi from 2023.5.7 to 2023.7.22 by @dependabot in #106

## 1.3.2
* Implement `set_by_path(obj, path, value)`

## 1.3.1
* Add ability to provide additional params to Aiohttp (AsyncFHIRClient) and Requests (SyncFHIRClient) request
* Make `authorization` param truly optional
* Support chained search without specifying resource #92

## 1.3.0
* Fix resource fetching for /fhir base urls #81
* is_valid should return OperationOutcome(data=data) #50
* OperationOutcome returns dumped json on save #53
* Format code

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
