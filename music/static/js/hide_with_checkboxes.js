$(document).ready( function() {
    $(".hide-with-checkboxes").click(function(event) {
        var elements_to_manage = document.getElementsByClassName("managed-by-checkboxes");
        Array.prototype.forEach.call(elements_to_manage, element => {
            element.style.display = 'list-item';
        });

        var checkboxes = document.getElementsByClassName("hide-with-checkboxes");
        Array.prototype.forEach.call(checkboxes, checkbox => {
            if (!checkbox.checked) {
                var elements_to_hide = document.getElementsByClassName(checkbox.name);
                Array.prototype.forEach.call(elements_to_hide, element => {
                    element.style.display = 'none';
                });
            }
        });
    });
});
