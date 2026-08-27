$(function () {
  $(".message").delay(3000).fadeOut(400);

  $(".remove-form").on("submit", function () {
    return confirm("Remove this ad from your wishlist?");
  });
});
