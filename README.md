Step 2: Install Datasette

Before we can run Datasette, we need to install it. We can do that using the following command:

pipx install datasette
This will install Datasette using pipx, which ensures it is kept in its own separate environment where it can't clash with any other Python code you may decide to run in your codespace.

To confirm that Datasette has installed successfully, run this:

datasette --version
We also need to install a plugin:

datasette install datasette-codespaces
The datasette-codespaces plugin makes some small changes to Datasette to better run in the Codespaces environment. You can run Datasette without it but you may run into some frustrating issues, such as internal links not working correctly.

Step 3: Start Datasette

To start Datasette, run this command:

datasette data.db --create
This will start Datasette running against an empty SQLite database called data.db. If that database does not exist yet it will be created.

You should see the following:

The terminal window shows Datasette outputting some INFO: log lines. A dialog is shown next to it which reads: Your applicaiton running on port 8001 is available - it provides a big green Open in Browser button

Click that "Open in Browser" button to open the Datasette web interface in a new browser tab.

If you can't see that button, check to see if the "Ports" tab is available in the Codespaces interface. You can use that to connect to your Datasette instance instead.

Step 4: Import some data

Your Datasette interface will start with an empty database. Let's add some data to it!

We'll do that using the sqlite-utils command line tool.

We can leave Datasette running in the background by starting a new terminal. Click on the word "python" at the top of the terminal window and select "Split terminal":

Clicking Python reviels a menu with several options - the top one is called Split Terminal

You should now have two terminal windows next to each other.

In the new terminal window, run this command to install sqlite-utils:

pipx install sqlite-utils
Then confirm installation with:

sqlite-utils --version
Screenshot of two terminal windows - the left one contains Datasette, while the right one shows a freshly installed copy of sqlite-utils.

Let's fetch a CSV file from the web:

wget https://static.simonwillison.net/static/2022/Manatee_Carcass_Recovery_Locations_in_Florida.csv

And insert it into our database:

sqlite-utils insert data.db locations \
    Manatee_Carcass_Recovery_Locations_in_Florida.csv \
    --csv -d
This creates a new table called locations containing the data from that CSV file - manatee carcass recovery locations in Florida dating back to 1974.

The --csv option tells sqlite-utils to treat the file as a CSV file, and the -d option tells it to infer the column types from the data (rather than treating every column as a text column).

See the tutorial Cleaning data with sqlite-utils and Datasette for more about this example data.

Step 5: Install some more plugins

Datasette has over 100 available plugins, listed in the plugins directory.

To install these, we first need to stop the Datasette server running. To do this first click back on the terminal window running Datasette and then hit Ctrl+C to stop the server.

The datasette install ... command installs new plugins. Let's install a few of them:

datasette install \
  datasette-vega \
  datasette-cluster-map \
  datasette-copyable \
  datasette-configure-fts \
  datasette-edit-schema \
  datasette-upload-csvs
Here's what each of these plugins does:

datasette-vega adds line, bar and scatter chart visualizations
datasette-cluster-map adds a map visualization for any table with latitude and longitude columns
datasette-copyable provides additional export options for copying and pasting data out of Datasette
datasette-configure-fts helps you to configure full-text search for your tables
datasette-edit-schema provides tools toedit the schema of your tables
Start the server running again like this: datasette data.db We don't need the --create option any more as we know the database already exists - although it won't break anything if we do include it.

Step 6: Explore those manatee locations on a map

In Datasette, navigate to that "locations" table. It should have columns called X and Y which look like they might contain latitude and longitude data.

The datasette-cluster-map plugin can render these all on a map... but only if the columns have the names latitude and longitude.

We can use the datasette-edit-schema plugin to rename those columns.

Click on the cog icon at the top of the table, then select "Edit table schema".

Screenshot of the Edit table data/locations screen, with a list of columns that can be changed. The first two have been renamed to longitude and latitude.
Rename the X and Y columns to longitude and latitude respectively, then click "Apply changes".

Return to the table page and you should see this map of Florida with manatee locations plotted on it:

Screenshot of Datasette showing a map of manatee locations in Florida

Next steps

Try working through the rest of the Cleaning data with sqlite-utils and Datasette tutorial to learn more about how to use sqlite-utils and Datasette together.

More tutorials

Exploring a database with Datasette
Learn SQL with Datasette
Cleaning data with sqlite-utils and Datasette
Building a location to time zone API with SpatiaLite
Data analysis with SQLite and Python
Powered by Datasette · How this site works · Code of conduct