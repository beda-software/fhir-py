## 1.0.0
This version breaks backward compatibility, but the main class structure and set of methods remain the same.
* Rework library and make separate sync (based on requests) and async (based on aiohttp client) versions
* Fix bug where we feed bytes instead of str to json.loads on success response
* Add fhir-4.0.0 schema
* Improved readme

## 0.2.0
* Fix requirements

## 0.1.2 
* Fix page method (use page instead of _page query param)

## 0.1.1
* Initial public release (based on aidbox-py)
