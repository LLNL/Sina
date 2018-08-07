@ECHO off
call :%1

goto :eof

:all
    call :migrate
    call :run
    goto :eof
:run
    python manage.py runserver 8080
    goto :eof
:run-all
    python manage.py runserver 0.0.0.0:8080
    goto :eof
:migrate
    python manage.py makemigrations sinaweb
    python manage.py migrate
    goto :eof
:count
    :: Get the number of commits, not using this for
    :: anything other than progress tracking
    git rev-list --all --count
    goto :eof
