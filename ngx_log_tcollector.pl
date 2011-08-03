#use File::Spec;
use File::ReadBackwards;

my $re_ipv4 = qr/(?:(?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2})[.](?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2})[.](?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2})[.](?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2}))/ixsm;
my $re_ipv4_nginx_xff = qr/(?:$re_ipv4)(?: \,? \s+ $re_ipv4)*/ixsm;
my $re_static = qr/\.(?:gif|png|jpg|jpeg|js|css|swf)/ixsm;
my $re_domain = qr/(?:[0-9A-Za-z](?:(?:[-A-Za-z0-9]){0,61}[A-Za-z0-9])?(?:\.[A-Za-z](?:(?:[-A-Za-z0-9]){0,61}[A-Za-z0-9])?)*)/ixsm;
my $re_uri = qr/[^ ]+/ixsm;
my $re_qstring = qr/(?:[^ ]+|-)/ixsm;
my $re_msec = qr/\d{10}\.\d{3}/ixsm;
my $re_status = qr/\d{3}|-/ixsm;
my $re_cost = qr/(?:\d+\.\d+|-|\d+)/ixsm;
my $re_static_err = qr/(?:5\d{2}|404)/ixsm;
my $re_dynamic_err = qr/(?:5\d{2})/ixsm;

sub do_parse {
    my $self = shift;
    my $rc_dynamic;
    my $bw = File::ReadBackwards->new('/dev/shm/nginx_metrics/metrics.log');
    if ($bw) {
        BACKWARD_READ:
        while (defined (my $line = $bw->readline)) {
            chomp $line;
            if ($line =~ /^($re_msec) \s+ ($re_domain|$re_ipv4) \s+ ($re_uri) \s+ ($re_status) \s+ ($re_ipv4:\d+|-) \s+ $re_ipv4_nginx_xff \s+ ($re_cost|-)$/ixsm) {
                my ($msec, $domain, $uri, $status, $upstream, $cost) = ($1, $2, $3, $4, $5, $6);
                $upstream =~ s/:\d+//g;
                if ($uri eq '-') {
                    next BACKWARD_READ;
                }
                if ($upstream eq '-') {
                    $cost = 0.003;
                    $upstream = '10.65.10.112';
                }
                if ($cost eq '-') {
                    next BACKWARD_READ;
                }
                $rc_dynamic->{$domain}->{$upstream}->{latency} += $cost;
                $rc_dynamic->{$domain}->{$upstream}->{throughput}++;
            }
        }
    return $rc_dynamic;
    }
}


my $rc_dynamic = &do_parse;
foreach my $domain (keys %{$rc_dynamic}) {
    foreach my $upstream (keys %{$rc_dynamic->{$domain}}) {
        my $errors = 0;
        unless (exists $rc_dynamic->{$domain}->{$upstream}->{error}) {
        $errors = 0;
        }
        METRIC_HANDLING:
        foreach my $item (keys %{$rc_dynamic->{$domain}->{$upstream}}) {
            if ($item eq 'throughput') {
                $results .= sprintf("put nginx.throughput %d %d domain=%s upstream=%s type=dynamic\n",
                time(),
                ($rc_dynamic->{$domain}->{$upstream}->{throughput}),
                $domain,
                $upstream,
                );
                print $results;

            }
        }
    }
}
