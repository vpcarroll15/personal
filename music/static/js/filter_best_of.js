$(document).ready( function() {
    $(".filter-best-of").click(function(event) {
        const elements_to_manage = document.getElementsByClassName("managed-by-checkboxes");
        Array.prototype.forEach.call(elements_to_manage, element => {
            element.style.display = 'none';
        });

        const radio_buttons = document.getElementsByName("filter-best-of");
        Array.prototype.forEach.call(radio_buttons, radio_button => {
            if (radio_button.checked) {
                const elements_to_reveal = document.getElementsByClassName(radio_button.value);
                Array.prototype.forEach.call(elements_to_reveal, element => {
                    element.style.display = 'list-item';
                });
            }
        });
    });
});
