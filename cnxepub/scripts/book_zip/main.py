from webcon import WebInterface
from subprocess import call

# Given a page name, returns the local address
def local_url_format(page_name):
    return page_name.encode('utf-8').replace(' ', '_') + ".html"

# Given a resource url, returns the local address
def resource_link_format(cnx_url):
    return "." + cnx_url[14:] # remove the cnx.org/contents

def setup_page(page_id, page_name, web_interface):
    """
    Pulls the page specified by page_id, and stores it as well as the resources it uses
    """
    web_interface.load_min_html(page_id)
    resources = web_interface.replace_resource_links(resource_link_format)
    
    page_html = web_interface.get_page_source()
    page_html = page_html.encode('utf-8')
    
    # Save this file
    f = open(page_name, "w")
    f.write(page_html)

    # Go through and pull resource files, make note of their location for zipping
    act_resources = []
    for resource in resources:
        web_interface.save_resource(resource, resource_link_format(resource))
        act_resources.append(resource_link_format(resource))
    
    f.close()
    
    return act_resources

def write_toc_element(html, json_tree, web_interface, resource_files_added):
    """
    Recursively write the html corresponding to the elements in json_tree to file
    """
    # If id is just subcol, there's no actual html associated w/ this page, so no link is required
    if(json_tree["id"] == "subcol"):
        html.write(json_tree["title"])
        html.write("<ul>\n")
        contents = json_tree["contents"]
        # Write each member of this tree
        for elem in contents:
            html.write("<li>\n")
            write_toc_element(html, elem, web_interface, resource_files_added)
            html.write("</li>\n")
        html.write("</ul>\n")

    # Otherwise, it's an individual page, link to it directly
    else:
        page_name = local_url_format(json_tree["title"])
        resource_files_added += setup_page(json_tree["id"], page_name, web_interface)
        main_files_added.append(page_name)
        html.write("<a href=\"" + page_name + "\">" + json_tree["title"].encode('utf-8') + "</a>\n")

"""
The actual script
"""
# For testing ,comment later
#page_id = "02040312-72c8-441e-a685-20e9333f3e1d@6.1"
# Test for a single page
#page_id = "ff9e026a-f3c3-441d-8685-36f788357041@1"
# Test for real openstax book
# page_id = "ffef104a-8aac-46f1-a8fd-c20a315e6d7a@4.2"
page_id = raw_input("Please enter page id: ")

main_files_added = []
resource_files_added = []

"""
Load TOC
"""
web_interface = WebInterface()
web_interface.load_toc(page_id)
book_title = web_interface.get_page_name();
print "Got toc for book: " + book_title + ", beginning toc html creation"

"""
Generate title page
"""
title_html = open('title.html', 'w')
main_files_added.append('title.html')
title_html.write("<html>\n")
title_html.write("<body>\n")

meta = web_interface.get_metadata()

# Add title name
title_html.write("<h1>Title: " + meta["title"] + "</h1>")

first = meta["first"]
title_html.write("<h2>Main Content: <a href=\"" + local_url_format(first) + "\">" + first + "</a></h2>")

# Add info about people
for group in meta["people"]:
    title_html.write("<h3>" + group + ":</h3>")
    title_html.write("<ul>\n")
    for person in meta["people"][group]:
        title_html.write("<li>" + person["fullname"] + "</li>\n")
    title_html.write("</ul>\n")

# Add revision date
title_html.write("<h3>Last revised: " + meta["revised"] + "</h3>")

# Add license info
title_html.write("<h3>License:</h3>")
title_html.write("<ul>")
title_html.write("<li>url: " + meta["license"]["url"] + "</li>")
title_html.write("<li>code: " + meta["license"]["code"] + "</li>")
title_html.write("<li>version: " + meta["license"]["version"] + "</li>")
title_html.write("<li>name: " + meta["license"]["name"] + "</li>")
title_html.write("</ul>")

# End title writing
title_html.write("</body>\n")
title_html.write("</html>\n")
title_html.close()


"""
Create the html TOC
"""
toc_html = open('toc.html', 'w') #TODO: Correct name?
main_files_added.append('toc.html')
toc_html.write("<html>\n")
toc_html.write("<body>\n")

toc_json = web_interface.get_tree()
#toc_html.write()
toc_html.write("<ul>")
for section in toc_json["contents"]:
    toc_html.write("<li>")
    write_toc_element(toc_html, section, web_interface, resource_files_added)
    toc_html.write("</li>")
toc_html.write("</ul>")

# Finish writing toc
toc_html.write("</body>\n")
toc_html.write("</html>\n")
toc_html.close()

print "Finished writing toc..."

"""
Shut things down
"""
web_interface.quit()

"""
Zip it all up, remove copies once done
"""

print "Zipping..."

unique_dirs = []
zip_command = ["zip",  "-rm", book_title]
for filename in main_files_added + resource_files_added:
    print "Adding file: " + filename + " to zip"
    zip_command.append(filename)
call(zip_command)

# Although individual resource files have been deleted, still need to remove 
# resources folder
rm_command = ["rm", "-r", "resources"]
call(rm_command)

print "Zip complete!"




