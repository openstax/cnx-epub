from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from urllib import urlretrieve
from os import makedirs
from os.path import exists
from pyvirtualdisplay import Display
 
class WebInterface:
    def __init__(self):
	display = Display(visible=0, size=(800, 600))
	display.start()

        #self.driver = webdriver.Chrome("/usr/local/lib/node_modules/chromedriver/lib/chromedriver/chromedriver")
	options = webdriver.ChromeOptions()
	options.binary_location = '/usr/bin/chromium-browser'
	self.driver = webdriver.Chrome('/usr/bin/chromedriver', chrome_options=options)

    def load_page(self, url):
        """
        Load the page located @ url
        """
        print "Getting: " + url
        # Navigate to the page
        self.driver.get(url)

        # Hold onto the json
        body = self.driver.find_element_by_tag_name("body")
        self.txt = body.text

        #TODO: Python is doing all the processing before page is done loading, so all the
        # pages just say "loading".  Is this an acceptable way of blocking until then?
        #TODO pt 2: might not be correct, could be somewhat loaded but not completely
        # as for ^, doesn't seem to have a tangible impact on page returned, i.e. full text whether or not we wait until a couple seconds afterwards
        while self.txt == "Loading...Loading..." or self.txt == "Loading...":
            self.txt = self.driver.find_element_by_tag_name("body").text

    def load_toc(self, page_id):
        """
        Load the table of contents (TOC) page of the page whose id is page_id
        """
        self.load_page("http://archive.cnx.org/contents/" + page_id + ".json")
        self.json = json.loads(self.txt) 
        
    def load_min_html(self, page_id):
        """
        Load the minimal html of the page whose id is page_id
        """
	print "Loading min html for page: http://cnx.org/contents/"+page_id+"?minimal=true";
        self.load_page("http://cnx.org/contents/" + page_id + "?minimal=true")
        
    def get_page_name(self):
        """
        Returns the title string of the currently loaded TOC page
        """
        return self.json["title"]
    
    def get_tree(self):
        """
        Returns the content tree (in json form) of the currently loaded TOC page
        """
        return self.json["tree"]
    
    def get_metadata(self):
        """
        For the currently loaded TOC page, returns the page title, the first page in the book,
        and information about revisions, licenses, and people involved (i.e. metadata for the
        title page).
        """
        
        # Find the title of the first page in the book
        cur_level = self.json["tree"]
        while True:
            cur_level = cur_level["contents"]
            sub_level = cur_level[0]
            if sub_level["id"] == "subcol":
                cur_level = sub_level
                continue
            else:
                first = sub_level["title"]
                break

        # Find names of unique editors
        editors = []
        for change in self.json["history"]:
            if change["publisher"] not in editors:
                editors.append(change["publisher"])            
        
        return {"title": self.json["title"], "revised": self.json["revised"], "license": self.json["license"], "parent": self.json["parent"], "people": {"Editors": editors, "Authors": self.json["authors"], "Publishers": self.json["publishers"], "Licensors": self.json["licensors"]}, "first": first}
    
    def get_page_source(self):
        """
        Returns the full html of the currently loaded page
        """
        return self.driver.page_source

    def replace_resource_links(self, html_modifier):
        """
        Given a function that translates cnx resource urls into
        the proper local resource format (ex: /resources/[hash]/[file]),
        modifies the loaded page source to contain the proper links, and returns
        the list of all resources that need to be pulled
        """
        resources = []

        tags = self.driver.find_elements(By.XPATH, "//*[@data-media-type]")
        for tag in tags:
            # If the href attribute exists, we'll use that to determine link
            url = tag.get_attribute("href")
            if url:
                url = url.encode('utf-8')
                self.driver.execute_script("arguments[0].setAttribute('href', '" + html_modifier(url) + "')", tag)

            # If not, try to find a src attribute
            else:
                url = tag.get_attribute("src")
                if url:
                    url = url.encode('utf-8')
                    self.driver.execute_script("arguments[0].setAttribute('src', '" + html_modifier(url) + "')", tag)

                # If all else fails, throw error, print out info
                else:
                    raise RuntimeError("Error: no url found for (apparent) resource: " + tag.text)

            # Keep note of the address where it's located
            resources.append(url)

        return resources
    
    def save_resource(self, resrc_url, save_name):
        """
        Given the url of a given resource, resrc_url, save it under the name
        save_name.  Will create the parent directories if they don't already
        exist
        """
        dir = "/".join(save_name.split("/")[:-1])
        if not exists(dir):
            print "creating dir: " + dir
            makedirs(dir)
        else:
            print dir + " already exists"
        
        urlretrieve(resrc_url, save_name)

    def quit(self):
        self.driver.quit()
