%define name rainbow

Summary: Rainbow
Name: %{name}
Version: %{version}
Release: %{release}%{?dist}
Source0: %{name}-%{version}.tar.gz
Source1: rainbow.conf
Source2: rainbow.logrotate
Source3: rainbow-public
Source4: rainbow-manage
Source5: rainbow-worker
Source6: rainbow-dba
Source7: rainbow-shell
Source8: rainbow-public.service
Source9: rainbow-manage.service
Source10: rainbow-worker.service
License: MIT
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: piaoyuankui@gmail.com <UNKNOWN>
Url: http://rainbow.com

Requires: python-flask = 1:0.10.1, python-sqlalchemy = 1.0.11, python-alembic = 0.8.3
Requires: python-redis = 2.10.3, python-jsonschema = 2.3.0, python2-PyMySQL = 0.6.7
Requires: python-keystoneclient = 1:2.3.1, python-neutronclient = 4.1.1, python-ceilometerclient = 2.3.0
Requires: python-ipython = 3.2.1
Requires: densefog >= 1.0.4

%description
UNKNOWN

%prep
%setup -n %{name}-%{version} -n %{name}-%{version}

%build
python setup.py build

%install
mkdir %{buildroot}/etc/rainbow -p
%{__install} -p -D -m 0755 %{SOURCE1} %{buildroot}/etc/rainbow/rainbow.conf
%{__install} -p -D -m 0644 %{SOURCE2} %{buildroot}/etc/logrotate.d/rainbow.logrotate
%{__install} -p -D -m 0755 %{SOURCE3} %{buildroot}/etc/init.d/rainbow-public
%{__install} -p -D -m 0755 %{SOURCE4} %{buildroot}/etc/init.d/rainbow-manage
%{__install} -p -D -m 0755 %{SOURCE5} %{buildroot}/etc/init.d/rainbow-worker
%{__install} -p -D -m 0755 %{SOURCE6} %{buildroot}/usr/local/bin/rainbow-dba
%{__install} -p -D -m 0755 %{SOURCE7} %{buildroot}/usr/local/bin/rainbow-shell
%{__install} -p -D -m 0755 %{SOURCE8} %{buildroot}/usr/lib/systemd/system/rainbow-public.service
%{__install} -p -D -m 0755 %{SOURCE9} %{buildroot}/usr/lib/systemd/system/rainbow-manage.service
%{__install} -p -D -m 0755 %{SOURCE10} %{buildroot}/usr/lib/systemd/system/rainbow-worker.service
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%pre

%post
mv /usr/bin/rainbow-dba /usr/bin/.rainbow-dba
mv /usr/bin/rainbow-shell /usr/bin/.rainbow-shell

%preun
if  [ $1 == 0 ];then
    rm -rf /usr/bin/.rainbow-dba 
    rm -rf /usr/bin/.rainbow-shell
    if [ ! -z "`ps aux | grep rainbow | grep -v grep`" ];then
        #killall -9 rainbow  >/dev/null
        systemctl stop rainbow-public.service
        systemctl stop rainbow-manage.service
        systemctl stop rainbow-worker.service
    fi
fi

%files -f INSTALLED_FILES
%defattr(-,root,root)
/etc/densefog/rainbow.conf
/etc/logrotate.d/rainbow.logrotate
/etc/init.d/rainbow-public
/etc/init.d/rainbow-manage
/etc/init.d/rainbow-worker
/usr/local/bin/rainbow-dba
/usr/local/bin/rainbow-shell
/usr/lib/systemd/system/rainbow-public.service
/usr/lib/systemd/system/rainbow-manage.service
/usr/lib/systemd/system/rainbow-worker.service

%config(noreplace) /etc/densefog/rainbow.conf
