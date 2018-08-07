/*
Functionality for adding fields dynamically to a form to be able to add
multiple fields to the create workflow form for things like adding variables
and steps.

Note: My JavaScript/jQuery is really rusty.
*/

$(document).ready(function(){
  // Add a new item with input when the `add variable` button is clicked.
  $("#btn-spec-var").click(function(){
    // This is definitly not the best way to do this. Better solution pending...
    item = 0; // Keep track of the number of items added
    addItem();
    item++;  // Increment after adding an item
  });
});

// Add an input field to the form.
function addInputToItem(){
    return "<input type='text' value='' />"
}

// Adds a semantic UI item (currently to the maestro variable form field).
// Note: It would be nice to make this a general component that can be used
// more generically since we'll likely have a few use cases for this.
function addItem(){
  // Create a new item div tag with the item count
  $("<div class='item" + item + "'><i class='icon minus'></i></div>")
      .prependTo(".spec-vars")

  // Add the input field to the newly created item.
  $(".item" + item).append(addInputToItem());
}
