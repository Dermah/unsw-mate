#!/usr/bin/perl -w

# written by Sputnik Antolovich (sant964@cse.unsw.edu.au) October 2012
# based on sample code and lab11 survey script by andrewt@cse

use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
use CGI::Cookie;
use HTML::Template;
use List::Util qw/min max/;

sub action_see_user();
sub action_gallery();
sub action_search();
sub action_login();
sub get_profile_pic($);
sub get_user_file($);
sub make_mate_list($);
sub get_mate_url($);
sub page_header(); 
sub page_trailer();

# print start of HTML ASAP to assist debugging if there is an error in the script
print page_header();
warningsToBrowser(1);

my %template_variables = (
   URL => url(),
   LOGIN_URL => url()."?action=login",
   TITLE => "UNSW-Mate",
   CGI_PARAMS => join(",", map({"$_='".param($_)."'"} param())),
   ERROR => "Unknown error"
);

# some globals used through the script
$debug = 1;
$users_dir = "./users";

my $page = "home_page";
my $action = param('action');
$action =~ s/[^a-zA-Z0-9\-_]//g;
# execute a perl function based on the CGI parameter 'action'
$page = &{"action_$action"}() if $action && defined &{"action_$action"};
# load HTML template from file based on $page value
my $template = HTML::Template->new(filename => "$page.template", die_on_bad_params => 0);
# put variables into the template
$template->param(%template_variables);
print $template->output;
print "</html>\n";
print page_trailer();
exit(0);

sub action_see_user() {
   my $username = param('username');
   $username =~ s/[^a-zA-Z0-9\-_]//g;
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
   open my $p, "$details_filename" or die "can not open $details_filename: $!";
   $details = join '', <$p>;
   close $p;
   @user_file = split "\n", $details;

   @user_file = get_user_file($username);

   for $elt (0..$#user_file) {
      if ($user_file[$elt] =~ /^name:/) {
         $template_variables{NAME} = $user_file[$elt+1];
      } elsif ($user_file[$elt] =~ /^gender:/) {
         $gender = $user_file[$elt+1];
         $gender =~ s/^\W*m/M/;
         $gender =~ s/^\W*f/F/;
         $template_variables{GENDER} = $gender;
      } elsif ($user_file[$elt] =~ /^degree:/) {
         $template_variables{DEGREE} = $user_file[$elt+1];
      }
   }
   $template_variables{PROFILE_PIC_URL} = get_profile_pic($username);
   $template_variables{GALLERY_URL} = url()."?action=gallery&username=".$username;
   $template_variables{DETAILS} = pre($details);
   $template_variables{MATE_LIST} = join " ", make_mate_list($username);
   $template_variables{NUM_MATES} = make_mate_list($username);
   #return p,
   #    start_form, "\n",
   #    submit('Random UNSW Mate Page'), "\n",
   #    pre($details),"\n",
   #    end_form, "\n",
   #    p, "\n";

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
   $gallery_list = "";
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
      $results .= "<li><a href=\"".url()."?action=see_user&username=$username\"><img src=\"".$user_path."/profile.jpg\" /></a> <a href=\"".url()."?action=see_user&username=$username\">$user</a></li>\n";
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
         while ($line !~ /^password:/) {
            $line = <DETAILS>;
         }
         $password = <DETAILS>;
         chomp $password;
         $password =~ s/\t(.+)$/$1/;
         if ($password eq param('password')) {
            $template_variables{MESSAGE} = "Login successful";
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
    return header,
        start_html(-title=>"UNSW Mate",-style=>{-src=>['style.css'],-media=>'all'});
}

#
# HTML placed at bottom of every screen
# It includes all supplied parameter values as a HTML comment
# if global variable $debug is set
#
sub page_trailer () {
    my $html = "";
    $html .= join("", map("<!-- CGI PARAMS: $_=".param($_)." -->\n", param())) if $debug;
    $html .= end_html;
    return $html;
}
