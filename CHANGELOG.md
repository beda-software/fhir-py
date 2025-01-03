## 2.0.15

* Remove trailing '/' from base url when building resource location path

## 2.0.14

* Minor type fixes

## 2.0.13

*  Add support for resource type and reference for client methods get/patch/delete (#133)

## 2.0.12

* Fix fetch_raw for custom resource class

## 2.0.11

* Rename dump to dump_resource
* Get rid of built-in dumping for dict-like structure
* Get rid of built-in dumping for patch
* Some breaking changes here, but the functional was introduced recently 
that's why the version is not increased according to semver
  * Migration guide for pydantic-users:
  * Pass `dump_resource=lambda d: d.model_dump()`
  * Manually dump your models for patch


## 2.0.10

* Update serializer with recursive cleaning and removing null values

## 2.0.9

* Update serializer with removing empty dicts/lists and transforming empty dicts into nulls in lists

## 2.0.8

* Add experimental pluggable client-level dump function

## 2.0.7

* Preserve null values for resource in save() with fields passed

## 2.0.6

* Fix type inference for client.resource
* Remove null values from dict for save/create/update
* Preserve null values in dict for patch

## 2.0.5
* Fix support for 3.9+ by adding missing typing-extensios as dependency #129

## 2.0.4
* Fix support for 3.9+ #129

## 2.0.3
* Fix typings for mypy for SearchSet

## 2.0.2
* Fix client.save type inference for TResource

## 2.0.1
* Fix backward compatibility for client resource/resources

## 2.0.0
* Add typehints for all methods
* Add pluggable data model #126
* Add client API for data model operations (CRUD)
* Add reference helpers for delete and patch #103
* BREAKING CHANGE: Changed internal module structure paths
  * There are private files structure, it should not affect the code that uses `fhirpy` and `fhirpy.base` public exports
  * `SyncResource`/`SyncReference`/`SyncSearchSet` moved from `base.lib` to `base.lib_sync`
  * `AsyncResource`/`AsyncReference`/`AsyncSearchSet` moved from `fhirpy.base.lib` to `fhirpy.base.lib_async`
  * `SyncClient` moved from `fhirpy.base.lib` to `fhirpy.base.lib_sync`
  * `AsyncClient` moved from `fhirpy.base.lib` to `fhirpy.base.lib_async`
  * `AbstractClient` moved from `fhirpy.base.lib` to `fhirpy.base.client`
  * `BaseResource`/`BaseReference` are available as part of public exports
* BREAKING CHANGE: Rename AbstractResource `client` to `__client__` #59
  * It's a private API, there's a small chance that it should not affect the code
* Deprecate conditional patch with resource argument, use kwargs instead
* Fix pickling error for BaseResource instances #77
* Add .execute for search set #74

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
