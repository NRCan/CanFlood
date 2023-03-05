# CanFlood Tests
The CanFlood test framework has gone through a few iterations as QGIS has expanded its plugin offerings. 

The current framework (tests2) makes use of the [pytest-qgis project](https://github.com/GispoCoding/pytest-qgis) which provides nice cleanups and fixtures for QGIS in [pytest](https://docs.pytest.org/en/7.1.x/).

Two types of tests are included:

 - unit tests (one for each toolset; i.e., 'test_build'). These should correspond to roughly one user 'action' or click on a given UI.
 - integration tests (one for each tutorial; i.e., 'test_t2.py'). These should closely follow the tutorials to reduce user frustration. 
 - api workflow tests. (TODO)

At the end of each test, a validation against some datafile (previous test result) should be performed to ensure program behavior/performance has not changed. 

## Calling tests
the batch script `./tests2/pytest_all.bat` is provided to conveniently run all of the "tests2" tests. 