#!/usr/bin/perl -w

# written by Sputnik Antolovich (sant964@cse.unsw.edu.au) October 2012
# based on sample code and lab11 survey script by andrewt@cse

use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
use CGI::Cookie;
use HTML::Template;
use List::Util qw/min max/;
use Digest::MD5 qw/md5_hex/;
use File::Path qw/remove_tree/;

sub action_see_user();
sub action_gallery();
sub action_search();
sub action_login();
sub action_logout();
sub action_delete();
sub action_create();
sub get_profile_pic($);
sub get_user_file($);
sub make_mate_list($);
sub get_mate_url($);
sub page_header(); 
sub page_trailer();
sub check_login();
sub setup_page_top_nav();


my %template_variables = (
   URL => url(),
   LOGIN_URL => url()."?action=login",
   CREATE_URL => url()."?action=create",
   TITLE => "UNSW-Mate",
   CGI_PARAMS => join(",", map({"$_='".param($_)."'"} param())),
   ERROR => "Unknown error"
);

# some globals used through the script
$debug = 1;
$users_dir = "./users";
$cookie_cache = "./cookies";
mkdir "$cookie_cache" if (!-d "$cookie_cache");

check_login;
setup_page_top_nav;

my $page = "home_page";
my $action = param('action');
$action =~ s/[^a-zA-Z0-9\-_]//g if $action;
# execute a perl function based on the CGI parameter 'action'
$page = &{"action_$action"}() if $action && defined &{"action_$action"};
# load HTML template from file based on $page value
my $template_header = HTML::Template->new(filename => "header.template", die_on_bad_params => 0);
my $template_toolbar = HTML::Template->new(filename => "toolbar.template", die_on_bad_params => 0);
my $template = HTML::Template->new(filename => "$page.template", die_on_bad_params => 0);
# put variables into the template
$template_header->param(%header_variables);
$template_toolbar->param(%toolbar_variables);
$template->param(%template_variables);

# print start of HTML ASAP to assist debugging if there is an error in the script
print page_header();
warningsToBrowser(1);

print $template_header->output;
print $template_toolbar->output if defined $toolbar_variables{VISIBILITY};
print $template->output;

print page_trailer();
exit(0);

sub action_see_user() {
   my $username = param('username');
   $username =~ s/[^a-zA-Z0-9\-_]//g if $username;
   if (! $username) {
       # for the purposes of level 0 testing if no username is supplied
       # we select a random username
       #
       # in level 1 if no username is supplied 
       # your website should allow a username to found by searching   
       # or a user tologin by supplying their username and password
    
       my @users = glob("$users_dir/*");
       $username = $users[rand @users];
       $username =~ s/.*\///;
   }
   $template_variables{USERNAME} = $username;

   my $details_filename = "$users_dir/$username/details.txt";
   return "error" if (! -r $details_filename);
   open my $p, "$details_filename" or die "can not open $details_filename: $!";
   my $details = join '', <$p>;
   close $p;
   my @user_file = split "\n", $details;

   @user_file = get_user_file($username);

   for my $elt (0..$#user_file) {
      if ($user_file[$elt] =~ /^name:/) {
         $template_variables{NAME} = $user_file[$elt+1];
      } elsif ($user_file[$elt] =~ /^gender:/) {
         my $gender = $user_file[$elt+1];
         $gender =~ s/^\W*m/M/;
         $gender =~ s/^\W*f/F/;
         $template_variables{GENDER} = $gender;
      } elsif ($user_file[$elt] =~ /^degree:/) {
         $template_variables{DEGREE} = $user_file[$elt+1];
      } elsif ($user_file[$elt] =~ /^courses:/) {
         $offset = 1;
         while ($user_file[$elt+$offset] =~ /\t/) {
            $template_variables{COURSE_LIST} .= "<li>";
            $line = $user_file[$elt+$offset];
            $line =~ s/\t//;
            $template_variables{COURSE_LIST} .= $line."</li>";
            $offset++;
         }
      }
   }
   $template_variables{PROFILE_PIC_URL} = get_profile_pic($username);
   $template_variables{GALLERY_URL} = url()."?action=gallery&username=".$username;
   $template_variables{DETAILS} = pre($details);
   $template_variables{MATE_LIST} = join " ", make_mate_list($username);
   $template_variables{NUM_MATES} = make_mate_list($username);

   if ($logged_in_user eq $username) {
      $toolbar_variables{VISIBILITY} = "visible";
      $toolbar_variables{CONTENTS} = "<span id=\"toolbar-left\"><a href=\"\">Edit Page</a></span><span id=\"toolbar-right\"><a href=\"".url()."?action=delete\">Delete Account</a></span>";
   }

   return "user_page";
}

sub action_gallery () {
   my $username = param('username');
   $username =~ s/[^a-zA-Z0-9\-_]//g;

   if (!$username) {
      die "Fake 403 Forbidden Error, no username specified for gallery";
   }

   $template_variables{PROFILE_PIC_URL} = get_profile_pic($username);
   $template_variables{PROFILE_URL} = url()."?action=see_user&username=".$username;
   $template_variables{GALLERY_THUMBS} = "Error while accessing this mates gallery, please try again";
   my @gallery_files = glob("$users_dir/$username/gallery*.jpg");
   my $gallery_list = "";
   for $image (@gallery_files) {
      $gallery_list .= "<img src=\"".$image."\" /> <br />\n";
   }
   $template_variables{GALLERY_THUMBS} = $gallery_list;
   return "gallery";
}

#
# Searches user names, not actual names
# May not handle spaces correctly yet
#
sub action_search () {
   my $term = param('term');
   my @matches = glob("$users_dir/*$term*");

   my $results = "";
   for $user_path (@matches) {
      $username = $user_path;
      $username =~ s/$users_dir\/([\w_-]+)/$1/;
      $user = $username;
      $user =~ s/_/ /g; 
      $results .= "<li><a href=\"".url()."?action=see_user&username=$username\"><img class=\"matelist-pic\" src=\"".$user_path."/profile.jpg\" /></a> <a class=\"matelist-namelink\" href=\"".url()."?action=see_user&username=$username\">$user</a></li>\n";
   }

   $template_variables{SEARCH_TERM} = $term;
   $template_variables{SEARCH_RESULTS} = $results;
   return "search";
}

sub action_login() {
   if (defined param('username') and defined param('password')) {
      my $username = param('username');
      $username =~ s/[^a-zA-Z0-9_-]//g;
      my $user_file = "$users_dir/$username/details.txt";
      if ($username ne param('username')) {
         $template_variables{MESSAGE} = "Incorrect username or password";
         return "login";
      } elsif (!-r "$user_file") {
         $template_variables{MESSAGE} = "Incorrect username or password";
      } else {
         open DETAILS, "$user_file" or die "Error opening login files, please try again";
         $line = "dummy:";
         while ($line !~ /^password:/) {
            $line = <DETAILS>;
         }
         $password = <DETAILS>;
         chomp $password;
         $password =~ s/\t(.+)$/$1/;
         if ($password eq param('password')) {
            $hash = md5_hex($username.localtime(time).rand());
            open my $H, '>', "$cookie_cache/$hash.$username" or die "Unable to create a cookie for you";
            print $H $hash.".".$username;
            $cookie = cookie (
                       -NAME => 'sessionID',
                       -VALUE => "$hash",
                       -EXPIRES => '+1d',
                    );
            $template_variables{MESSAGE} = "Login successful!";
            print redirect(
               -URL=> url(),
               -COOKIE => $cookie
            );
            exit 0;
         } else {
            $template_variables{MESSAGE} = "Incorrect username or password";
         }
      }
      $password = param('password');
   } else {
      $template_variables{MESSAGE} = "Please enter your username and password below";
   }
   return "login";
}

sub action_logout() {
   if (defined cookie('sessionID')) {
      my $hash = cookie('sessionID');
      $hash =~ s/[^a-z0-9A-Z]//g;
      if (-r "$cookie_cache/$hash.$logged_in_user") {
         unlink("$cookie_cache/$hash.$logged_in_user");
         $cookie = cookie(
                    -NAME => 'sessionID',
                    -VALUE => "",
                    -EXPIRES => '+0s'
                   );
         print redirect(
                  -URL => url(),
                  -COOKIE => $cookie
               );
         exit 0;
      } else {
         $cookie = cookie(
                    -NAME => 'sessionID',
                    -VALUE => "",
                    -EXPIRES => '+0s'
                   );
         print redirect(
                  -URL => url(),
                  -COOKIE => $cookie
               );
         exit 0;
      }
   } else {
      return "home_page";
   }
}

sub action_delete() {
   if (!$logged_in_user) {
      $template_variables{MESSAGE} = "You must be logged in to delete your account";
      $template_variables{VISIBILITY} = "collapse";
   } elsif (param('confirm') eq "true") {
      my $hash = cookie('sessionID');
      $hash =~ s/[^a-zA-Z0-9]//g;
      if (-r "$cookie_cache/$hash.$logged_in_user") {
         my $removal = "$users_dir/$logged_in_user";
         remove_tree($removal) or die "Broke trying to remove user directory $removal";
         unlink("$cookie_cache/$hash.$logged_in_user");
         $cookie = cookie(
                    -NAME => 'sessionID',
                    -VALUE => "",
                    -EXPIRES => '+0s'
                   );
         $template_variables{MESSAGE} = "Sorry to see you go. Your account has been deleted";
         $template_variables{VISIBILITY} = "collapse";
      } else {
         $template_variables{MESSAGE} = "Error deleting your account (you don't appear to be logged in)";
         $template_variables{VISIBILITY} = "collapse";
      }
   } else {
      $template_variables{MESSAGE} = "Are you sure you want to delete your account? This cannot be undone!";
   }
   return "delete";
}

sub action_create() {
   sleep(2);
   $template_variables{FORM_USERNAME} = param('username');
   $template_variables{FORM_EMAIL} = param('email');
   if (param('username') eq "" or param('password') eq "" or param('password2') eq "" or param('email') eq "" or param('email2') eq "") {
      $template_variables{MESSAGE} = "One or more of the fields below were empty, please try again";
      return "create";      
   }

   $username = param('username');
   $username =~ s/[^a-zA-Z0-9\-_]//g;
   if ($username ne param('username')) {
      $template_variables{MESSAGE} = "Usernames may only have letters, numbers, hyphens and underscores in them. Please try again";
      return "create";
   }
   if (param('password') ne param('password2')) {
      $template_variables{MESSAGE} = "The passwords you entered didn't match. Please try again";
   }

   $email = param('email');
   $email =~ s/[^a-zA-Z0-0\-_@\.]//g;
   if ($email ne param('email')) {
      $template_variables{MESSAGE} = "We can't send mail to this email address, please try another one";
   } elsif ($email !~ /\w+@\w\.\w/) {
      $template_variables{MESSAGE} = "Invalid email address, please try again";
   }

   if (param('email') ne param('email2')) {

   }

   return "create";
}

#
# Arg: username
# Returns: relative URL of the specified username's profile picture
# Current;y does not check that it exists
#
sub get_profile_pic ($) {
   my ($username) = @_;
   $url = "$users_dir/$username/profile.jpg";
   return $url;
}

#
# Arg: username
# Returns: array of contents of username's details.txt
# Currently does not check if username exists
#
sub get_user_file ($) {
   my ($username) = @_;
   my $details_filename = "$users_dir/$username/details.txt";
   open my $p, "$details_filename" or die "can not open $details_filename: $!";
   $details = join '', <$p>;
   close $p;
   return split "\n", $details;
}

#
# Gets a name from a username
#
sub get_name_from_user ($) {
   my ($username) = @_;
   my @detail_file = get_user_file($username) or die "Could not find specified user: $username";
   for my $elt (0..$#detail_file) {
      if ($detail_file[$elt] eq "name:") {
         return $detail_file[$elt+1];
      }
   }
}

#
# Arg: username
# Returns: list of mates in format <li><a href="MATE_URL"><img src="MATE_PROFILE_PIC">MATE_NAME</a></li>
# Does not check if username is valid
# In scalar context, returns number of mates 
# 
sub make_mate_list ($) {
   my ($username) = @_;
   my @user_file = get_user_file($username);
   for my $elt (0..$#user_file) {
      if ($user_file[$elt] =~ /^mates:/) {
         while ($user_file[$elt+1] =~ /\W+\w/) {
            my $line = $user_file[$elt+1];
            $line =~ s/\W*([\w_-]+)\W*/$1/;
            $user = $line;
            $user_nounder = $line;
            $user_nounder =~ s/_/ /g;
            $line = "<li><a href=\"".get_mate_url($user)."\"><img class=\"matelist-pic\" src=\"".get_profile_pic($user)."\"/></a> ";
            $line .= "<a class=\"matelist-namelink\" href=\"".get_mate_url($user)."\">".$user_nounder."</a></li>\n";
            push @mates_names, $line;
            $elt++;
         }
      }
   }
   return @mates_names;
}

#
# Arg: username
# Returns: url of the specified username
# Doesn't check if it's valid
#
sub get_mate_url ($) {
   my ($username) = @_;
   $url = url()."?action=see_user&username=".$username;
   return $url;
}

#
# HTML placed at the top of every screen
#
sub page_header () {
    return header(
              -COOKIE=>$cookie
           ),
           start_html(
              -TITLE => "UNSW Mate",
              -STYLE => {-src=>['style.css'],-media=>'all'},
           );
}

#
# HTML placed at bottom of every screen
# It includes all supplied parameter values as a HTML comment
# if global variable $debug is set
#
sub page_trailer () {
    my $html = "";
    $html .= join("", map("<!-- CGI PARAMS: $_=".param($_)." -->\n", param())) if $debug;
    $html .= "<!-- Cookie for sessionID: ".cookie('sessionID')."-->\n" if defined cookie('sessionID');
    $html .= end_html;
    return $html;
}

#
# Checks cookie to see if user is already logged in
#
sub check_login() {
   if (defined cookie('sessionID')) {
      my $hash = cookie('sessionID');
      $hash =~ s/[^a-z0-9A-Z]//g;
      my $cookie_path = glob ("$cookie_cache/$hash.*");
      if ($cookie_path) {
         $logged_in_user = $cookie_path;
         $logged_in_user =~ s/$cookie_cache\/$hash.(\w+)/$1/;
         $logged_in_name = get_name_from_user($logged_in_user);
         $template_variables{LOGGED_IN_USER} = $logged_in_user;
         $template_variables{LOGGED_IN_NAME} = $logged_in_name;
      } else {
         $cookie = cookie(
                    -NAME => 'sessionID',
                    -VALUE => "",
                    -EXPIRES => '+0s'
                   );
      }
   }
}

sub setup_page_top_nav() {
   $header_variables{SCRIPT_URL} = url();
   
   $header_variables{LOGGED_IN_NAME} = "Login";
   $header_variables{LOGGED_IN_NAME} = $logged_in_name if defined $logged_in_name;
   
   if (defined $logged_in_user) {
      $header_variables{LOGGED_IN_URL} = get_mate_url($logged_in_user);
      $header_variables{PROFILE_PIC} = get_profile_pic($logged_in_user);
      $header_variables{LOGOUT_URL} = url()."?action=logout";
      $header_variables{LOGOUT} = "Logout";
   } else {
      $header_variables{LOGGED_IN_URL} = url()."?action=login";
      $header_variables{PROFILE_PIC} = "./nopicture.jpg";
   }
}
