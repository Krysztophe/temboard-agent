%global pkgname temboard-agent
%{!?pkgversion: %global pkgversion 1.1}
%{!?pkgrevision: %global pkgrevision 1}

%{!?python_sitelib: %global python_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}

Name:          %{pkgname}
Version:       %{pkgversion}
Release:       %{pkgrevision}%{?dist}
Summary:       temBoard agent

Group:         Applications/Databases
License:       PostgreSQL
URL:           http://temboard.io/
Source0:       %{pkgname}-%{version}.tar.gz
Source1:       temboard-agent.init
Source2:       temboard-agent.service
Patch1:        temboard-agent.conf.patch
BuildArch:     noarch
BuildRequires: python-setuptools
Requires:      openssl
%if 0%{?rhel} <= 6
Requires: python-argparse
Requires: python-logutils
%endif
Requires:      python-setuptools

%description
Administration & monitoring PostgreSQL agent.


%prep
%setup -q -n %{pkgname}-%{version}
%patch1 -p1


%build
%{__python} setup.py build

%pre
# This comes from the PGDG rpm for PostgreSQL server. We want temboard to run
# under the same user as PostgreSQL
groupadd -g 26 -o -r postgres >/dev/null 2>&1 || :
useradd -M -n -g postgres -o -r -d /var/lib/pgsql -s /bin/bash \
        -c "PostgreSQL Server" -u 26 postgres >/dev/null 2>&1 || :


%install
PATH=$PATH:%{buildroot}%{python_sitelib}/%{pkgname}
%{__python} setup.py install --root=%{buildroot}
# config file
%{__install} -d -m 755 %{buildroot}/%{_sysconfdir}
%{__install} -d -m 750 %{buildroot}/%{_sysconfdir}/temboard-agent
%{__install} -m 600 %{buildroot}/usr/share/temboard-agent/temboard-agent.conf %{buildroot}/%{_sysconfdir}/temboard-agent/temboard-agent.conf
%{__install} -d -m 755 %{buildroot}/%{_sysconfdir}/logrotate.d
%{__install} -m 644 %{buildroot}/usr/share/temboard-agent/temboard-agent.logrotate %{buildroot}/%{_sysconfdir}/logrotate.d/temboard-agent
# init script
%if 0%{?rhel} <= 6
%{__install} -d %{buildroot}%{_initrddir}
%{__install} -m 755 %{SOURCE1} %{buildroot}%{_initrddir}/temboard-agent
rm -f %{buildroot}/usr/lib/systemd/system/temboard-agent*.service
%endif

%if 0%{?rhel} >= 7
%{__install} -d %{buildroot}%{_unitdir}
%{__install} -m 644 %{SOURCE2} %{buildroot}%{_unitdir}/temboard-agent.service
%endif

# log directory
%{__install} -d %{buildroot}/var/log/temboard-agent
# work directory
%{__install} -d %{buildroot}/var/lib/temboard-agent/main
# pidfile directory
%{__install} -d %{buildroot}/var/run/temboard-agent
%{__install} -m 600 /dev/null %{buildroot}/%{_sysconfdir}/temboard-agent/users

%post
# auto-signed SSL cert. building
openssl req -new -x509 -days 365 -nodes -out /etc/pki/tls/certs/temboard-agent.pem -keyout /etc/pki/tls/private/temboard-agent.key -subj "/C=XX/ST= /L=Default/O=Default/OU= /CN= " >> /dev/null 2>&1


%if 0%{?rhel} >= 7
systemctl daemon-reload
if systemctl is-active temboard-agent &>/dev/null; then
    systemctl restart temboard-agent
fi
%endif


%files
%config(noreplace) %attr(-,postgres,postgres) %{_sysconfdir}/temboard-agent
%config(noreplace) %{_sysconfdir}/logrotate.d/temboard-agent
%{python_sitelib}/*
/usr/share/temboard-agent/*
/usr/bin/temboard-agent*

%if 0%{?rhel} <= 6
%{_initrddir}/temboard-agent
%endif

%if 0%{?rhel} >= 7
%{_unitdir}/temboard-agent.service
%{_unitdir}/temboard-agent@.service
%endif

%attr(-,postgres,postgres) /var/log/temboard-agent
%attr(-,postgres,postgres) /var/lib/temboard-agent
%config(noreplace) %attr(0600,postgres,postgres) /etc/temboard-agent/users

%preun
%if 0%{?rhel} >= 7
systemctl stop temboard-agent
systemctl disable temboard-agent
%endif


%postun
%if 0%{?rhel} >= 7
systemctl daemon-reload
%endif


%changelog
* Wed Nov 8 2017 Julien Tachoires <julmon@gmail.com> - 1.1-1
- Handle systemd service on uninstall
- Build auto-signed SSL certs
- Set up users file as a config file
- Remove centos 5 support

* Mon Jul 4 2016 Nicolas Thauvin <nicolas.thauvin@dalibo.com> - 0.0.1-1
- Initial release
