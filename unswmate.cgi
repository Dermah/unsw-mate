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
use File::Copy;
use File::Glob qw(:globally :nocase);

sub action_see_user();
sub action_gallery();
sub action_edit_gallery();
sub action_search();
sub action_login();
sub action_logout();
sub action_delete();
sub action_create();
sub action_verify();
sub action_edit_user();
sub action_request();
sub action_manage_requests();
sub get_profile_pic($);
sub get_user_file($);
sub does_user_exist($);
sub get_user_file_hash($);
sub write_hash_to_user($%);
sub make_mate_list($);
sub get_mate_url($);
sub page_header(); 
sub page_trailer();
sub check_login();
sub setup_page_top_nav();

# some globals used through the script
$debug = 1;
$users_dir = "./users";
$cookie_cache = "./cookies";
$verify_dir = "./toverify";
mkdir "$cookie_cache" if (!-d "$cookie_cache");
$login_url = url()."?action=login";                     #optional &username=
$create_url = url()."?action=create";
$gallery_url = url()."?action=gallery&username=";       #needs username
$edit_url = url()."?action=edit_user";
$edit_gallery_url = url()."?action=edit_gallery";
$delete_url = url()."?action=delete";
$profile_url = url()."?action=see_user";                #optional &username=
$request_url = url()."?action=request&user=";           #needs username
$manage_requests_url = url()."?action=manage_requests";
$finder_url = url()."?action=finder";                    #optional &start=

my %template_variables = (
   URL => url(),
   LOGIN_URL => $login_url,
   CREATE_URL => $create_url,
   TITLE => "UNSW-Mate",
   CGI_PARAMS => join(",", map({"$_='".param($_)."'"} param())),
   ERROR => "Unknown error"
);

check_login;
setup_page_top_nav;

my $page = "home_page";
my $action = param('action');
$action =~ s/[^a-zA-Z0-9\-_]//g if $action;
# execute a perl function based on the CGI parameter 'action'
$page = &{"action_$action"}() if $action && defined &{"action_$action"};
# load HTML template from file based on $page value
my $template = HTML::Template->new(filename => "$page.template", die_on_bad_params => 0);
my $template_header = HTML::Template->new(filename => "header.template", die_on_bad_params => 0);
my $template_toolbar = HTML::Template->new(filename => "toolbar.template", die_on_bad_params => 0);
# put variables into the template
$template->param(%template_variables);
$template_header->param(%header_variables);
$template_toolbar->param(%toolbar_variables);

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

   $username =~ s/[^a-zA-Z0-9\-_]//g;

   if (does_user_exist($username) ne "yes") {
      $template_variables{MESSAGE} = "Could not find user $username";
      $template_variables{STATUS} = "error";
      return "status";
   }

   $template_variables{USERNAME} = $username;
   @user_details = get_user_file($username);
   %details = get_user_file_hash($username);
   
   $template_variables{NAME} = $details{name};
   my $gender = $details{gender};
   $gender =~ s/^m/M/;
   $gender =~ s/^f/F/;
   $template_variables{GENDER} = $gender;
   $template_variables{DEGREE} = $details{degree};
   if ($details{courses} ne "") {
      my @course_array = split "\n", $details{courses};
      my $course_list = "<li>";
      $course_list .= join "</li>\n<li>", @course_array;
      $course_list .= "</li>";
      $template_variables{COURSE_LIST} = $course_list;
   } else {
      $template_variables{COURSE_LIST} = "No courses completed";
   }

   $template_variables{PROFILE_PIC_URL} = get_profile_pic($username);
   $template_variables{GALLERY_URL} = $gallery_url.$username;
   $template_variables{DETAILS} = pre($file_details);
   $template_variables{MATE_LIST} = join " ", make_mate_list($username);
   $template_variables{NUM_MATES} = make_mate_list($username)/2;

   #page and account editing toolbar
   if ($logged_in_user eq $username) {
      $toolbar_variables{VISIBILITY} = "visible";
      $toolbar_variables{CONTENTS} = "<span id=\"toolbar-left\"><a href=\"".$edit_url."\">Edit Page</a> | <a href=\"".$finder_url."\">Mate Finder</a></span><span id=\"toolbar-right\"><a href=\"".$delete_url."\">Delete Account</a></span>";
   } elsif ($logged_in_user) {
      $toolbar_variables{VISIBILITY} = "visible";
      %logged_in_details = get_user_file_hash($logged_in_user);
      $toolbar_variables{CONTENTS} = "<span id=\"toolbar-left\"><a href=\"".$request_url.$username."\">Send Mate Request</a></span>";
      foreach $mate (split "\n", $logged_in_details{mates}) {
         $toolbar_variables{CONTENTS} = "You are mates with <b>$template_variables{NAME}</b>" if $username eq $mate;
      }
   }
   
   my $about_me_file = "$users_dir/$username/about_me.txt";
   
   if (-r $about_me_file) {
      open ABOUT, $about_me_file or die "Could not open about me file $about_me_file";
      my $about_me = "";
      while (my $line = <ABOUT>) {
         $line =~ s/\</\&lt\;/g;
         $line =~ s/\>/\&gt\;/g;
         $about_me .= $line."<br />";
      }
      $template_variables{ABOUT_ME} = $about_me;
   } else {
      $template_variables{ABOUT_ME} = "This user hasn't provided any information about themselves!";
   }

   return "user_page";
}

sub action_gallery () {
   my $username = param('username');
   $username =~ s/[^a-zA-Z0-9\-_]//g;

   if (!$username) {
      $template_variables{MESSAGE} = "No gallery found, please try again";
      $template_variables{STATUS} = "error";
      return "status";
   }

   %details = get_user_file_hash($username);

   $template_variables{NAME} = $details{name};
   $template_variables{PROFILE_PIC_URL} = get_profile_pic($username);
   $template_variables{PROFILE_URL} = $profile_url."&username=".$username;
   $template_variables{GALLERY_THUMBS} = "This user has no gallery pictures";

   my @gallery_files = glob("$users_dir/$username/gallery*.jpg");
   my $gallery_list = "";
   for $image (@gallery_files) {
      $gallery_list .= "<img src=\"".$image."\" /> <br />\n";
   }
   $template_variables{GALLERY_THUMBS} = $gallery_list if ($gallery_list ne "");

   #page and account editing toolbar
   if ($logged_in_user eq $username) {
      $toolbar_variables{VISIBILITY} = "visible";
      $toolbar_variables{CONTENTS} = "<span id=\"toolbar-left\"><a href=\"".$edit_gallery_url."\">Edit Gallery</a></span>";
   }

   return "gallery";
}

sub action_edit_gallery() {
   if (!$logged_in_user) {
      $template_variables{MESSAGE} = "You must be logged in to edit your gallery";
      $template_variables{STATUS} = "error";
      return "status";
   }

   my @gallery_files = glob("$users_dir/$logged_in_user/gallery*.jpg");
   if (!@gallery_files) {
      $new_location = "gallery00.jpg";
   } else {
      $new_location = $gallery_files[$#gallery_files];
      $new_location =~ s/.*?gallery([0-9]+).jpg/$1/;
      while (glob("$users_dir/$logged_in_user/gallery$new_location.jpg")) {
         $new_location++;
      }
   }
   
   if (defined param('upload') and param('upload') eq "Upload" and param('filename') ne "") {
      my $pic_filename = param('filename');
      open PIC, '>', "$users_dir/$logged_in_user/gallery-temp.jpg";
      print PIC $_ while <$pic_filename>;
      close PIC;
      system ("convert -resize 650x650 \"$users_dir/$logged_in_user/gallery-temp.jpg\" \"$users_dir/$logged_in_user/gallery$new_location.jpg\"");
      unlink("$users_dir/$logged_in_user/gallery-temp.jpg");
   }

   if (defined param('delete')) {
      $to_delete = param('delete');
      $to_delete =~ s/[^0-9]//g;
      if (-r "$users_dir/$logged_in_user/gallery$to_delete.jpg") {
         unlink("$users_dir/$logged_in_user/gallery$to_delete.jpg");
         $template_variables{MESSAGE} =  "Picture deleted successfully";
         $template_variables{STATUS} = "success";
      } else {
         $template_variables{MESSAGE} = "That picture doesn't exist";
         $template_variables{STATUS} = "error";
      }
   }

   @gallery_files = glob("$users_dir/$logged_in_user/gallery*.jpg");
   %details = get_user_file_hash($logged_in_user);

   $template_variables{NAME} .= $details{name};
   $template_variables{PROFILE_PIC_URL} = get_profile_pic($logged_in_user);
   $template_variables{PROFILE_URL} = $profile_url."&username=".$logged_in_user;
   $template_variables{GALLERY_THUMBS} = "This user has no gallery pictures";

   my $gallery_list = "";
   for $image (@gallery_files) {
      $img_no = $image;
      $img_no =~ s/.*?gallery([0-9]+).jpg/$1/;
      $gallery_list .= "<a href=\"".$edit_gallery_url."&delete=".$img_no."\"><img class=\"gallery-edit-delete\" src=\"cross.png\" /></a> Picutre no. $img_no <br/>\n";
      $gallery_list .= "<img class=\"gallery-picture\" src=\"".$image."\" /> <br />\n";
   }
   $template_variables{GALLERY_THUMBS} = $gallery_list if ($gallery_list ne "");

   #page and account editing toolbar
   $toolbar_variables{VISIBILITY} = "visible";
   $toolbar_variables{CONTENTS} = "<span id=\"toolbar-left\"><a href=\"".$gallery_url.$logged_in_user."\">Cancel</a></span>";

   return "gallery";
}

#
# Searches user names, not actual names
# May not handle spaces correctly yet
# case insensitive
#
sub action_search () {
   $term = param('term');
   $term =~ s/[^a-zA-Z0-9\-_]//g;
   my @matches = glob("$users_dir/*$term*");

   my $results = "";
   for $user_path (@matches) {
      $username = $user_path;
      $username =~ s/$users_dir\/([\w_-]+)/$1/;
      $user = $username;
      $results .= "<li><a href=\"".$profile_url."&username=$username\"><img class=\"matelist-pic\" src=\"".$user_path."/profile.jpg\" /></a> <a href=\"".$profile_url."&username=".$username."\">$user</a></li>\n";
   }

   $template_variables{SEARCH_TERM} = $term;
   $template_variables{SEARCH_RESULTS} = $results;
   return "search";
}

sub action_login() {
   sleep(2); #to prevent bruteforce attack
   if (defined param('username') and defined param('password')) {
      my $username = param('username');
      $username =~ s/[^a-zA-Z0-9_-]//g;
      if ($username ne param('username')) {
         $template_variables{MESSAGE} = "Incorrect username or password";
         return "login";
      } elsif (does_user_exist($username) eq "") {
         $template_variables{MESSAGE} = "Incorrect username or password";
      } else {
         %details = get_user_file_hash($username);
         $password = $details{password};
         if ($password eq param('password')) {
            # Login successful, plants a cookie and redirects browser to home page
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
   } else {
      $template_variables{MESSAGE} = "Please enter your username and password below";
   }
   return "login";
}

sub action_logout() {
   if (defined cookie('sessionID')) {
      my $hash = cookie('sessionID');
      $hash =~ s/[^a-z0-9A-Z]//g;
      unlink("$cookie_cache/$hash.$logged_in_user") if (-r "$cookie_cache/$hash.$logged_in_user");
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
         my %details = get_user_file_hash($logged_in_user);
         my $mates = $details{mates};
         my @mate_array = split "\n", $mates;
         foreach $mate (@mate_array) {
            my %mate_det = get_user_file_hash($mate);
            @checking_mates = split "\n", $mate_det{mates};
            $mate_det{mates} = "";
            foreach $check_mate (@checking_mates) {
               $mate_det{mates} .= $check_mate."\n" if $check_mate ne "$logged_in_user";
            }
            if (-r "$users_dir/$mate/details.txt") {
               open $USERFILE, '>', "$users_dir/$mate/details.txt" or die "Could not create details file at $users_dir/$mate/details.txt";
               #format a hash for printing to details.txt
               for my $key (keys %mate_det) {
                  my @lines = split "\n", $mate_det{$key};
                  my $line = "\t";
                  $line .= join "\n\t", @lines;
                  print $USERFILE "$key:\n$line\n";
               }
               close $USERFILE;         
            }
         }
         my $removal = "$users_dir/$logged_in_user";
         remove_tree($removal) or die "Broke trying to remove user directory $removal";
         # NEED TO DELETE USER FROM MATES LISTS
         unlink("$cookie_cache/$hash.$logged_in_user");
         $cookie = cookie(
                    -NAME => 'sessionID',
                    -VALUE => "",
                    -EXPIRES => '+0s'
                   );

         $template_variables{MESSAGE} = "Sorry to see you go. Your account has been deleted";
         $template_variables{VISIBILITY} = "collapse";
      } else {
         $template_variables{MESSAGE} = "Error deleting your account (you don't appear to be logged in, try logging out and back in)";
         $template_variables{VISIBILITY} = "collapse";
      }
   } else {
      $template_variables{MESSAGE} = "Are you sure you want to delete your account? This cannot be undone!";
   }
   return "delete";
}

sub action_create() {
   sleep(2); # to prevent bruteforce attack
   $template_variables{FORM_USERNAME} = param('username');
   $template_variables{FORM_EMAIL} = param('email');
   $template_variables{FORM_EMAIL2} = param('email2');
   $template_variables{NAME} = param('name');
   $template_variables{DEGREE} = param('degree');
   
   if (!defined param('username')) {  
      return "create";
   } elsif ((param('username') eq "") or (param('password') eq "") or (param('password2') eq "") or (param('email') eq "") or (param('email2') eq "") or (param('name') eq "")) {
      $template_variables{MESSAGE} = "One or more of the fields below were empty, please try again";
      $template_variables{STATUS} = "error";
      return "create";      
   }

   $username = param('username');
   $username =~ s/[^a-zA-Z0-9\-_]//g;
   if ($username ne param('username')) {
      $template_variables{MESSAGE} = "Usernames may only have letters, numbers, hyphens and underscores in them. Please try again";
      $template_variables{STATUS} = "error";
      return "create";
   }
   
   $name = param('name');
   $name =~ s/[^a-zA-Z\- ]//g;
   if ((param('name') ne $name)) {
      $template_variables{MESSAGE} = "Names can currently only have letters, spaces and hyphens in them. Please try again";
      $template_variables{STATUS} = "error";
      return "create";
   }

   $gender = param('gender');
   $gender =~ s/[^a-z]//g;
   $degree = param('degree');
   $degree =~ s/[^a-zA-Z\/\-\_\(\)\[\]\&\! ]//g;

   $email = param('email');
   $email =~ s/[^a-zA-Z0-9\-_@\.\!\#\$\%\&\'\*\+\-\/\=\?\^_\`\{\|\}\~]//g;
   $template_variables{FORM_EMAIL} = $email;
   if ($email ne param('email')) {
      $template_variables{MESSAGE} = "We can't send mail to this email address, please try another one";
      $template_variables{STATUS} = "error";
      return "create";
   } elsif ($email !~ /\w+\@\w+\.\w+/) {
      $template_variables{MESSAGE} = "Invalid email address, please try again";
      $template_variables{STATUS} = "error";
      return "create";
   } elsif (param('email') ne param('email2')) {
      $template_variables{MESSAGE} = "The email addresses you entered did not match. Please try again";
      $template_variables{STATUS} = "error";
      return "create";
   }
   if ((-r "$users_dir/$username") or (-r "$verify_dir/$username")) {
      $template_variables{MESSAGE} = "The username \"$username\" is already taken, please try another one";
      $template_variables{STATUS} = "error";
      return "create";
   }
   if (param('password') ne param('password2')) {
      $template_variables{MESSAGE} = "The passwords you entered didn't match. Please try again";
      $template_variables{STATUS} = "error";
      return "create";
   }

   mkdir $verify_dir if !-d $verify_dir;
   my $hash = md5_hex($username.localtime(time).rand());
   open my $H, '>', "$verify_dir/$username" or die "can not open verification file $username";
   print $H $hash."\n";
   print $H "password:\n";
   print $H "\t".param('password')."\n";
   print $H "email:\n";
   print $H "\t".$email."\n";
   print $H "name:\n";
   print $H "\t".$name."\n";
   print $H "gender:\n";
   print $H "\t".$gender."\n";
   print $H "degree:\n";
   print $H "\t".$degree."\n";
   print $H "courses:\n";
   print $H "\t\n";
   
   $verify_url = url()."?action=verify&key=$hash&user=$username";

   open F, '|-', 'mail', '-s', 'Verification from UNSW-Mate', $email or die "Cant send email to $address";
   print F "Hi there,\n\n";
   print F "Please use this URL to activate your UNSW-Mate account:\n";
   print F "$verify_url\n\n";
   print F "If you didn't sign up to UNSW-Mate then please ignore this email";
   close F;

   $template_variables{MESSAGE} = "A verification email has been sent to $email, your account will be activated once you click the link within";
   $template_variables{STATUS} = "success";
   $template_variables{VISIBILITY} = "collapse";

   return "create";
}

sub action_verify() {
   my $user = param('user');
   if (defined param('user')) {
      $user =~ s/[^a-zA-Z0-9\-_]//g;
      if (-r "$verify_dir/$user") {
         open VERIFILE, "$verify_dir/$user" or die "couldn't open the verification file";
         my $hash = <VERIFILE>;
         chomp $hash;
         if (param('key') eq $hash) {
         } else {
            $template_variables{STATUS} = "error";
            $template_variables{MESSAGE} = "The link you clicked seems to be incorrect. Try copying and pasting the URL again";
            return "status";
         }
      } else {
         $template_variables{STATUS} = "error";
         $template_variables{MESSAGE} = "No one has registered with the username \"$user\"";
         return "status";
      }      
   } else {
      $template_variables{STATUS} = "error";
      $template_variables{MESSAGE} = "An error has occured. Try copying and pasting the URL again";
      return "status";
   }
   
   mkdir "$users_dir/$user" or die "Could not create user data at $users_dir/$user";
   open $USERFILE, '>', "$users_dir/$user/details.txt" or die "Could not create details file at $users_dir/$user/details.txt";
   while ($line = <VERIFILE>) {
      print $USERFILE $line;
   }
   close $USERFILE;
   close VERIFILE;
   unlink("$verify_dir/$user");
   
   copy("nopicture.jpg", "$users_dir/$user/profile.jpg") or die "Could not create profile picture";

   $template_variables{STATUS} = "success";
   $template_variables{MESSAGE} = "Your email has been verified and your account has been activated. You can now login using the link above.";

   return "status";
}

sub action_edit_user() {
   if (!$logged_in_user) {
      $template_variables{MESSAGE} = "You have to be logged in to edit your profile";
      $template_variables{STATUS} = "error";
      return "status";
   }

   if ((defined param('edit') and (param('edit') eq "Save")) or (defined param('del_course'))) {
      $template_variables{MESSAGE} = "You are attempting to edit your profile! Woo!";
      $template_variables{STATUS} = "success";
      
      $about_me = param('about_me');
      undef $about_me if $about_me =~ /^\W*$/;
      if (!defined $about_me) {
         unlink "$users_dir/$logged_in_user/about_me.txt"
      } else {
         open $F, '>', "$users_dir/$logged_in_user/about_me.txt" or die "Could not write about me";
         $about_me =~ s/\</\&lt\;/g;
         $about_me =~ s/\>/\&gt\;/g;
         print $F $about_me;
         close $F;
      }

      %details = get_user_file_hash($logged_in_user);

      $details{gender} = param('gender') if param('gender') =~ /^.*\w+.*$/;
      $details{degree} = param('degree') if param('degree') =~ /^.*\w+.*$/;
      $not_first_course = "\n" if $details{courses} ne "";
      $details{courses} .= $not_first_course.param('new_course') if param('new_course') =~ /^.*\w+.*$/;

      if (param('del_course')) {
          my @courses = split "\n", $details{courses};
          $details{courses} = "";
          $counter = 1;
          for my $course (@courses) {
             $details{courses} .= $course."\n" if $counter != param('del_course');
             $counter++;
          }
      }
      chomp $details{courses};

      $details{$_} =~ s/\</&lt;/g for keys %details;
      $details{$_} =~ s/\>/&gt;/g for keys %details;

      if (-r "$users_dir/$logged_in_user/details.txt") {
         open $USERFILE, '>', "$users_dir/$logged_in_user/details.txt" or die "Could not create details file at $users_dir/$user/details.txt";
         #format a hash for printing to details.txt
         for my $key (keys %details) {
            @lines = split "\n", $details{$key};
            $line = "\t";
            $line .= join "\n\t", @lines;
            print $USERFILE "$key:\n$line\n";
         }
         close $USERFILE;         
      } else {
         $template_variables{MESSAGE} = "Bit of a problem, sorry chap";
         $template_variables{STATUS} = "error";
         return "status";
      }

      if (param('filename') ne "") {
         my $pic_filename = param('filename');
         open PIC, '>', "$users_dir/$logged_in_user/profile-temp.jpg";
         print PIC $_ while <$pic_filename>;
         close PIC; 
         system ("convert -resize 250x250 \"$users_dir/$logged_in_user/profile-temp.jpg\" \"$users_dir/$logged_in_user/profile.jpg\"");
         unlink("$users_dir/$logged_in_user/profile-temp.jpg");
      }

      $template_variables{MESSAGE} = "Your profile was successfully changed!";
      $template_variables{STATUS} = "success";
   }
   
   %details = get_user_file_hash($logged_in_user);

   $delete_html1 = "<button class=\"edit-del-button\" type=\"submit\" name=\"del_course\" value=\"";
   $delete_html2 = "\"><img src=\"cross.png\" \/></button>";

   # this and the identical code in see_user should be consolidated
   $template_variables{NAME} = $details{name};
   chomp $template_variables{NAME};
   my $gender = $details{gender};
   chomp $gender;
   $gender =~ s/^\W*m/M/;
   $gender =~ s/^\W*f/F/;
   $template_variables{GENDER} = $gender;
   $template_variables{MALE_SEL}   = "selected=\"selected\"" if $gender =~ /^Male$/;
   $template_variables{FEMALE_SEL} = "selected=\"selected\"" if $gender =~ /^Female$/;
   $template_variables{DEGREE} = $details{degree};
   chomp $template_variables{DEGREE};

   if ($details{courses} ne "") {
      $del_num = 1;
      my @course_array = split "\n", $details{courses};
      my $course = shift @course_array;
      my $course_list = "<li>".$delete_html1.$del_num.$delete_html2." $course";
      for $course (@course_array) {
         $del_num++;
         $course_list .= "</li>\n<li>".$delete_html1.$del_num.$delete_html2." $course";
      }
      $course_list .= "</li>";
      $template_variables{COURSE_LIST} = $course_list;
   } else {
      $template_variables{COURSE_LIST} = "<li>No courses added</li>";
   }

   my $about_me_file = "$users_dir/$logged_in_user/about_me.txt";
   
   if (-r $about_me_file) {
      open ABOUT, $about_me_file or die "Could not open about me file $about_me_file";
      my $about_me = "";
      while (my $line = <ABOUT>) {
         $line =~ s/\</\&lt\;/g;
         $line =~ s/\>/\&gt\;/g;
         $about_me .= $line;
      }
      $template_variables{ABOUT_ME} = $about_me;
   }

   $template_variables{PROFILE_URL} = $profile_url."&username=".$logged_in_user;
   $template_variables{PROFILE_PIC_URL} = get_profile_pic($logged_in_user);
   $template_variables{GALLERY_URL} = $gallery_url.$logged_in_user;
   $template_variables{DETAILS} = pre($file_details);
   $template_variables{MATE_LIST} = join " ", make_mate_list($logged_in_user);
   $template_variables{NUM_MATES} = make_mate_list($logged_in_user);

   #page and account editing toolbar
   $toolbar_variables{VISIBILITY} = "visible";
   $toolbar_variables{CONTENTS} = "<span id=\"toolbar-left\"><a href=\"".url()."?action=see_user&username=$logged_in_user\">Cancel</a></span><span id=\"toolbar-right\"><a href=\"".url()."?action=delete\"></a></span>";

   return "edit_user";
}

sub action_request () {
   if (!$logged_in_user) {
      $template_variables{MESSAGE} = "Please <a href=\"".$login_url."\">log in</a> to send mate requests";
      $template_variables{STATUS} = "error";
      return "status";
   } else {
      %logged_in_details = get_user_file_hash($logged_in_user);
      foreach $mate (split "\n", $logged_in_details{mates}) {
         if ($mate eq param('user')) {
            $template_variables{MESSAGE} = "You are already mates with $mate";
            $template_variables{STATUS} = "error";
            return "status";
         }
      }
      $user = param('user');
      $user =~ s/[^a-zA-Z0-9\-\_]//g;
      if (does_user_exist($user) ne "yes") {
         $template_variables{MESSAGE} = "User $user does not exist";
         $template_variables{STATUS} = "error";
         return "status";
      }
      mkdir "$users_dir/$user/requests" if (!-d "$users_dir/$user/requests");
      if (-r "$users_dir/$user/requests/$logged_in_user") {
         $template_variables{MESSAGE} = "You've already sent this user a friend request";
         $template_variables{STATUS} = "error";
         return "status";
      } elsif (-r "$users_dir/$logged_in_user/requests/$user") {
         $template_variables{MESSAGE} = "This user has already sent you a request. You can manage your friend requests <a href=\"".$manage_requests_url."\">here</a>";
         $template_variables{STATUS} = "error";
         return "status";
      } else {
         open $F, '>', "$users_dir/$user/requests/$logged_in_user" or die "Could not send request for some reason";
         print $F "request";
         close $F;

         %mate_det = get_user_file_hash($user);

         open E, '|-', 'mail', '-s', "Mate request from $logged_in_user", $mate_det{email} or die "Cant send email to $address";
         print E "Hi there,\n\n";
         print E "$logged_in_details{name} has sent you a Mate request on UNSW-Mate. Please use the linke below to accept or remove the request\n";
         print E "$manage_requests_url\n\n";
         print E "Thanks for using UNSW-Mate!";
         close E;

         $template_variables{MESSAGE} = "Friend request sent";
         $template_variables{STATUS} = "success";
      }
   }
   return "status";
}

sub action_manage_requests () {
   if (!$logged_in_user) {
      $template_variables{MESSAGE} = "Please <a href=\"".$login_url."\">log in</a> to manage your friend requests";
      $template_variables{STATUS} = "error";
      return "status";
   }
   if (defined param('accept') or defined param('cancel')) {
      if (param('accept') eq param('cancel')) {
         $template_variables{MESSAGE} = "Don't do that";
         $template_variables{STATUS} = "error";
         return "status";
      }
      if (defined param('accept')) {
         $to_accept = param('accept');
         $to_accept =~ s/[^a-zA-Z0-9\-\_]//g;
         if (!-r "$users_dir/$logged_in_user/requests/$to_accept") {
            $template_variables{MESSAGE} = "You don't have a freind request from $to_accept";
            $template_variables{STATUS} = "error";
            return "status";
         }
         
         my %details = get_user_file_hash($logged_in_user);
         my $first_mate = "";
         $first_mate = "\n" if ($details{mates} ne "");
         $details{mates} .= $first_mate.$to_accept;
         my %mate_det = get_user_file_hash($to_accept);
         $first_mate = "";
         $first_mate = "\n" if ($mate_det{mates} ne "");
         $mate_det{mates} .= $first_mate.$logged_in_user;
         write_hash_to_user($logged_in_user, %details);
         write_hash_to_user($to_accept, %mate_det);

         unlink("$users_dir/$logged_in_user/requests/$to_accept") or die "could not remove request";          

         $template_variables{MESSAGE} = "Friend request accepted";
         $template_variables{STATUS} = "success";
      }
      if (defined param('cancel')) {
         $to_cancel = param('cancel');
         $to_cancel =~ s/[^a-zA-Z0-9]//g;
         if (!-r "$users_dir/$logged_in_user/requests/$to_cancel") {
            $template_variables{MESSAGE} = "You don't have a freind request from $to_cancel";
            $template_variables{STATUS} = "error";
            return "status";
         }
         unlink("$users_dir/$logged_in_user/requests/$to_cancel") or die "could not remove request";
         $template_variables{MESSAGE} = "Friend request cancelled";
         $template_variables{STATUS} = "success";
      }
   }
   

   $template_variables{REQUEST_LIST} = "";
   @requests = glob ("$users_dir/$logged_in_user/requests/*");
   foreach $request (@requests) {
      $request =~ s/$users_dir\/$logged_in_user\/requests\/([\w\_]+)/$1/;
      if (does_user_exist($request)) {
         %mate_det = get_user_file_hash($request) if (does_user_exist($request) ne "");
         $template_variables{REQUEST_LIST} .= "<div class=\"managerequests-request\">";
         $template_variables{REQUEST_LIST} .= "<img class=\"managerequests-picture\" src=\"".get_profile_pic($request)."\" /> <a href=\"".$profile_url."&username=$request\">".$mate_det{name}."</a> sent you a mate request";
         $template_variables{REQUEST_LIST} .= "<span class=\"managerequests-buttons\"><b><a href=\"".$manage_requests_url."&accept=$request\">Accept</a></b> or <a href=\"".$manage_requests_url."&cancel=$request\">Cancel</a></span>";
         $template_variables{REQUEST_LIST} .= "</div>" ;
      }
   }

   if (@requests == 0) {
      $template_variables{REQUEST_LIST} = "You have no mate requests";
      $header_variables{REQ_VIS} = "hidden";
   }
   return "manage_requests";
}

sub action_finder () {
   if (!$logged_in_user) {
      $template_variables{MESSAGE} = "<a href=\"".$login_url."\">Log in</a> to find potential friends";
      $template_variables{STATUS} = "error";
      return "status";
   }

   foreach my $user (glob ("$users_dir/*")) {
      $user =~ s/$users_dir\/([a-zA-Z0-9\-\_]+)/$1/;
      my %user_det = get_user_file_hash($user);
      my @users_courses = (split "\n", $user_det{courses});
      foreach my $course (@users_courses) {
         $courses{$course}{$user} = "completed";
      }
   }

   my %details = get_user_file_hash($logged_in_user);
   foreach my $course (split "\n", $details{courses}) {  
      $you_may_know{$_}++ foreach keys %{$courses{$course}};
   }

   foreach my $mate (split "\n", $details{mates}) {
      my %mate_det = get_user_file_hash($mate);
      $you_may_know{$_}++ foreach (split "\n", $mate_det{mates});
   }

   $highest_rating = 0;
   foreach my $key (keys %you_may_know) {
      $highest_rating = $you_may_know{$key} if ($highest_rating < $you_may_know{$key});
      $you_may_know{$key} = 0 if $key eq $logged_in_user;
   }

   $counter = 0;
   foreach $rating (0..$highest_rating-1) {
      foreach $user (keys %you_may_know) {
         push @knowing_array, $user if $you_may_know{$user} == $highest_rating-$rating;
      }
   }

   $min = 0 if !defined param('start');
   $min = param('start') if defined param('start');
   $min =~ s/[^0-9]//g;
   $up_to = 0;
   foreach $num ($min..($min+9)) {
      last if $num > $#knowing_array;
      %mate_det = get_user_file_hash($knowing_array[$num]) if (does_user_exist($knowing_array[$num]) ne "");
      $template_variables{KNOW_LIST} .= "<div class=\"finder-entry\">";
      $template_variables{KNOW_LIST} .= "<img class=\"finder-picture\" src=\"".get_profile_pic($knowing_array[$num])."\" /> <a href=\"".$profile_url."&username=$knowing_array[$num]\">".$mate_det{name}."</a>";
      $template_variables{KNOW_LIST} .= " ($you_may_know{$knowing_array[$num]} mate and course connections)";
      $template_variables{KNOW_LIST} .= "</div>";
      $up_to = $num +1;
   }
   $template_variables{NEXT_LINK} = "<a class=\"finder-nextlink\" href=\"".$finder_url."&start=$up_to\">Next 10 &gt;&gt;</a>" if $up_to < $#knowing_array;

   return "finder";

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
   $file_details = join '', <$p>;
   close $p;
   return split "\n", $file_details;
}

sub does_user_exist($) {
   my ($username) = @_;
   my $details_filename = "$users_dir/$username/details.txt";
   return "yes" if (-r "$details_filename");
   return "";
}

#
# Arg: username
# Returns: hash of username's details.txt
#
sub get_user_file_hash ($) {
   my ($username) = @_;
   my $details_file = "$users_dir/$username/details.txt";
   my %details;
   if (-r $details_file) {
      open DETAILS, $details_file or die "Could not open user details";
      while ($line = <DETAILS>) {
         if ($line =~ /^(\w+):/) {
            $key = $1;
            $details{$key} = "";
         } elsif ($line =~ /^\t(.+)$/) {
            $details{$key} .= $1;
            $details{$key} .= "\n" if ($key eq "courses" or $key eq "mates");
         }
      }
   }
   chomp $details{courses};
   chomp $details{mates};
   return %details;
}

#
# Arg: username, details hash of username
# Writes details hash to the users detail file
#
sub write_hash_to_user ($%) {
   my ($username, %details) = @_;
   open $USERFILE, '>', "$users_dir/$username/details.txt" or die "Could not create details file at $users_dir/$username/details.txt";
   #format a hash for printing to details.txt
   for my $key (keys %details) {
      my @lines = split "\n", $details{$key};
      my $line = "\t";
      $line .= join "\n\t", @lines;
      print $USERFILE "$key:\n$line\n";
   }
   close $USERFILE;         
}

#
# Gets a name from a username
#
sub get_name_from_user ($) {
   my ($username) = @_;
   my %details  = get_user_file_hash($username);
   return $details{name};
}

#
# Arg: username
# Returns: list of mates in format <li><a href="MATE_URL"><img src="MATE_PROFILE_PIC">MATE_NAME</a></li>
# Does not check if username is valid
# In scalar context, returns number of mates 
# 
sub make_mate_list ($) {
   my ($username) = @_;
   my %details = get_user_file_hash($username);
   foreach $user (split "\n", $details{mates}) {
      $user_nounder = $user;
      $user_nounder =~ s/_/ /g;
      $line ="<li><a href=\"".get_mate_url($user)."\"><img class=\"matelist-pic\" src=\"".get_profile_pic($user)."\"/></a> ";
      $line .= "<a class=\"matelist-namelink\" href=\"".get_mate_url($user)."\">".$user_nounder."</a></li>\n";
      push @mates_names, $line;
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
   if ($debug) {
      $html .= join("", map("<!-- CGI PARAMS: $_=".param($_)." -->\n", param()));
      $html .= "<!-- Cookie for sessionID: ".cookie('sessionID')."-->\n" if defined cookie('sessionID');
   }
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
   $header_variables{REQ_VIS} = "collapse" if @requests == 0;
   
   if (defined $logged_in_user) {
      @requests = glob("$users_dir/$logged_in_user/requests/*");
      $header_variables{LOGGED_IN_NAME} = $logged_in_name if defined $logged_in_name;
      $header_variables{REQUESTS} = @requests if @requests > 0;
      $header_variables{REQ_VIS} = "visible" if @requests > 0;
      $header_variables{MANAGE_REQUESTS_URL} = $manage_requests_url;
      
      $header_variables{LOGGED_IN_URL} = get_mate_url($logged_in_user);
      $header_variables{PROFILE_PIC} = get_profile_pic($logged_in_user);
      $header_variables{LOGOUT_URL} = url()."?action=logout";
      $header_variables{LOGOUT} = "Logout";      
   } else {
      $header_variables{LOGGED_IN_URL} = url()."?action=login";
      $header_variables{PROFILE_PIC} = "./nopicture.jpg";
   }
}
