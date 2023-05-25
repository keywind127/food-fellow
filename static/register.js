function register() {
    let username = document.getElementById("email").value;
    let password = document.getElementById("password").value;
    $.ajax({
        "url" : "/register",
        "method" : "POST",
        "contentType" : "application/json",
        "dataType" : "json",
        "data" : JSON.stringify({ "username" : username, "password" : password }),
        "success" : function(response) {
            let registerStatus = response["status"];
            if (registerStatus == "already-logged-in") {
                console.log("ERROR: already logged in!");
            } 
            else if (registerStatus == "register-success") {
                console.log("SUCCESS: registration success! activation pending..");
                window.location.href = "/";
            }
            else if (registerStatus == "already-registered") {
                console.log("ERROR: registration already complete!");
            }
            else if (registerStatus == "register-failure") {
                console.log("ERROR: invalid email address!");
            }
            else {
                console.log("ERROR: invalid email or password!");
            }
        }
    })
}