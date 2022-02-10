# Inkbunny

A Python wrapper for the [Inkbunny](https://inkbunny.net/) API.


## DISCLAIMER
**I have no idea what I'm doing!**

- I'm not a programmer.
- I have next to no experience with Python (or any other language for that matter).
- I have no affiliation with Inkbunny.
- This project exists because I couldn't find a Python wrapper anywhere else.
- This is still very much a work in progress.
- I'm trying my best, but my best isn't very good.

**Use this wrapper at your own risk**




## Installation

```
pip install inkbunny
```
## Requirements
- Python ≥ 3.10.2
- [Requests](https://docs.python-requests.org/en/latest/)
- [platformdirs](https://github.com/platformdirs/platformdirs) (for now, at least)




## Usage

**TODO**
 
```python
from inkbunny import Inkbunny


```

<!-- ### context manager -->

```python
with Inkbunny() as ib:
    submission_results = ib.search('fox', results_count=1000)

print(submission_results)
```
<!-- 
(logs in as guest)

### asdf lower level 

api_* method names

 -->