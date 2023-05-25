function login() {
    let username = document.getElementById("email").value;
    let password = document.getElementById("password").value;
    $.ajax({
        "url" : "/login",
        "method" : "POST",
        "contentType" : "application/json",
        "dataType" : "json",
        "data" : JSON.stringify({ "username" : username, "password" : password }),
        "success" : function(response) {
            let statusCode = response["status"];
            if (statusCode == "login-success") {
                console.log("SUCCESS: login successful!");
                window.location.href = "/";
            }
            else if (statusCode == "already-logged-in") {
                console.log("ERROR: already logged in!");
            }
            else if (statusCode == "incorrect-password") {
                console.log("ERROR: incorrect password!");
            }
            else if (statusCode == "invalid-username") {
                console.log("ERROR: user not registered!");
            }
            else if (statusCode == "access-denied") {
                console.log("ERROR: service denied!");
            }
            else {
                console.log("ERROR: invalid email or password!");
            }
        }
    })
}