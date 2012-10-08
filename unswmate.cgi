#!/usr/bin/perl -w

# written by Sputnik Antolovich (sant964@cse.unsw.edu.au) September 2012
# based on sample code and lab11 survey script
# by andrewt@cse

use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
use HTML::Template;
use List::Util qw/min max/;

# print start of HTML ASAP to assist debugging if there is an error in the script
print page_header();
warningsToBrowser(1);

my %template_variables = (
   URL => url(),
   TITLE => "UNSW-Mate",
   CGI_PARAMS => join(",", map({"$_='".param($_)."'"} param())),
   ERROR => "Unknown error"
);

# some globals used through the script
$debug = 1;
$users_dir = "./users";

my $page = "home_page";
my $action = param('action');
# execute a perl function based on the CGI parameter 'action'
$page = &{"action_$action"}() if $action && defined &{"action_$action"};
# load HTML template from file based on $page value
my $template = HTML::Template->new(filename => "$page.template", die_on_bad_params => 0);
# put variables into the template
$template->param(%template_variables);
print $template->output;
print "</html>";
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
   $template_variables{USERNAME} = $username;
   return "user_page";
}


print browse_screen();
print page_trailer();
exit 0; 


sub browse_screen {
    my $details_filename = "$users_dir/$username/details.txt";
    open my $p, "$details_filename" or die "can not open $details_filename: $!";
    $details = join '', <$p>;
    close $p;
    
    return p,
        start_form, "\n",
        submit('Random UNSW Mate Page'), "\n",
        pre($details),"\n",
        end_form, "\n",
        p, "\n";
}

#
# HTML placed at the top of every screen
#
sub page_header {
    return header,
        start_html("-title"=>"UNSW Mate", -bgcolor=>"#FEDCBA"),
}

#
# HTML placed at bottom of every screen
# It includes all supplied parameter values as a HTML comment
# if global variable $debug is set
#
sub page_trailer {
    my $html = "";
    $html .= join("", map("<!-- $_=".param($_)." -->\n", param())) if $debug;
    $html .= end_html;
    return $html;
}
