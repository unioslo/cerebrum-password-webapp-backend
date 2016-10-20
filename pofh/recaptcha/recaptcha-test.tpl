<!DOCTYPE html>
<html>
    <head>
        <title>ReCAPTCHA test page</title>
        <script src="https://www.google.com/recaptcha/api.js"></script>
        <script src="https://code.jquery.com/jquery-3.1.1.js"
                integrity="sha256-16cdPddA6VdVInumRGo6IbivbERE8p7CQR3HzTBuELA="
                crossorigin="anonymous"></script>
        <script type="text/javascript">
            var setRecaptchaResponse = function(value) {
                $('textarea#recaptcha').val(value);
                $('input[type="submit"]').removeAttr('disabled');
            };
            var showResponse = function(xhr) {
                var response = "" + xhr.status + " " + xhr.statusText + "\n";
                response += xhr.getAllResponseHeaders() + "\n";
                response += xhr.responseText;
                $('<hr>').appendTo($('div#response'));
                $('<h2>Validate response</h2>').appendTo($('div#response'));
                var plain = $('<pre>');
                plain.text(response);
                plain.appendTo($('div#response'));
            };
            var doPost = function(ev) {
                ev.preventDefault();
                $('#response').html('')
                $.ajax(
                    {
                        type: $('#data').attr('method'),
                        url: $('#data').attr('action'),
                        data: $('#data').serialize()
                    }
                ).fail(
                    function(xhr, st, err) {
                        if (console && console.log) {
                            console.log(st, ":", err);
                            console.log(xhr);
                        }
                        showResponse(xhr);
                    }
                ).done(
                    function(data, st, xhr) {
                        if (console && console.log) {
                            console.log(st, ":", data);
                            console.log(xhr);
                        }
                        showResponse(xhr);
                    }
                );
            };
            var updateSubmit = function() {
                if ($('textarea#recaptcha').val()) {
                    $('input[type="submit"]').removeAttr('disabled');
                } else {
                    $('input[type="submit"]').attr('disabled', 'disabled');
                }
            }

            $().ready(
                function() {
                    $('form#data').submit(doPost);
                    updateSubmit();
                    $('textarea#recaptcha').change(updateSubmit);
                    $('textarea#recaptcha').val('');
                    setInterval(updateSubmit, 500);
                }
            );
        </script>
    </head>

    <body>
        <div id="content">
            <h1>ReCAPTCHA test page</h1>
            <p>This page can be used to test the ReCAPTCHA setup.</p>

            <div class="g-recaptcha"
                 data-sitekey="{{ site_key }}"
                 data-callback="setRecaptchaResponse"></div>

            <form id="data" method="POST" action="{{ action }}">
                <label for="recaptcha">Recaptcha response</label>
                <br/>
                <textarea id="recaptcha" rows="10" cols="120"
                          name="{{ field | default('g-recaptcha-response') }}">
                </textarea>
                <br />
                <input type="submit" value="Validate recaptcha"/>
            </form>

            <div id="response"></div>
        </div>
    </body>
</html>
