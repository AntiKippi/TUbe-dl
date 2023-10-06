# TUbe-dl
Is a simple tool to download playlists from [TUbe](https://portal.tuwien.tv). 
Since TUbe is powered by [Planet eStream](https://www.planetestream.co.uk/) this might work for other Planet eStream platforms as well.

## Requirements
 - Python v3.6 or higher
 - Some basic confidence in working with the terminal and IT knowledge
 - Access to TUbe

## Installation
Installation is performed via git by cloning this repository. 
Then you have to ensure that you have installed all the required packages listed in `requirements.txt`.

```
$ git clone https://github.com/AntiKippi/TUbe-dl.git
$ cd TUbe-dl
$ pip install -r requirements.txt
```

After that the `TUbe-dl.py` script is ready to use.

## Usage
To download a playlist you need to specify the URL (`-u`), the directory to put the videos in (`-o`) and the cookie (`-c`) used to access the site.

For a full description of all available options see `TUbe-dl.py -h`.

### Obtaining the cookie
Obtaining the cookie is by far the most difficult part. I am not happy with how complicated this is and might implement a better method in the future. 
Also if you have an easier method for obtaining the cookie, feel free to open a pull request.

One way to obtain the cookie in Firefox or Chrome is given below.

#### Firefox
 - Press <kbd>F12</kbd>
 - Go to the "Network" tab
 - Refresh the page
 - Select the first item in the now populated list
 - In the now shown pane on the right scroll down to the "Cookie" request header
 - Make a right click on it and select "Copy value"

<!--TODO: Video-->

#### Chrome
 - Press <kbd>F12</kbd>
 - Go to the "Network" tab
 - Refresh the page
 - Select the first item in the now populated list
 - In the now shown pane on the right scroll down to the "Cookie" request header
 - Triple click the content of the "Cookie" header and copy it with <kbd>CTRL</kbd> + <kbd>C</kbd>

<!--TODO: Video-->
 

## Bugs
If you find a bug please create an issue in this repository.

## Donations
I currently don't accept donations. However, if you find my work useful and want to say "Thank you!" consider starring this repository ⭐.