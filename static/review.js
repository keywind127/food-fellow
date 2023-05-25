function submit_review() {
    let foodName = document.getElementById("food_name").value;
    let restaurantName = document.getElementById("restaurant_name").value;
    let foodPrice = document.getElementById("food_price").value;
    let serviceRating = document.getElementById("service_rating").value;
    let foodRating = document.getElementById("food_rating").value;
    let recommendRating = document.getElementById("recommend_rating").value;
    let descriptiveTags = document.getElementById("descriptive_tags").value;
    console.log(foodName);
    console.log(restaurantName);
    console.log(foodPrice);
    console.log(serviceRating);
    console.log(foodRating);
    console.log(recommendRating);
    console.log(descriptiveTags);
    $.ajax({
    "url" : "/write",
    "method" : "POST",
    "contentType" : "application/json",
    "dataType" : "json",
    "data" : JSON.stringify({ 
        "food-name" : foodName,
        "restaurant-name" : restaurantName,
        "food-price" : foodPrice,
        "service-rating" : serviceRating,
        "food-rating" : foodRating,
        "recommend-rating" : recommendRating,
        "hashtags" : [ descriptiveTags ]
    }),
    "success" : function(response) {
        console.log("SUCCESS"); 
        console.log(response);
        if (response["status"] == "write-success") {
            window.location.href = "/";
        }
    }
})
}