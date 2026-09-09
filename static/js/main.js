/**
 * IT Career Hub - script dùng chung.
 *
 * Toàn bộ chức năng ở đây chỉ là tăng cường trải nghiệm (progressive
 * enhancement): tắt JavaScript thì mọi form và liên kết vẫn hoạt động bình
 * thường vì việc kiểm tra dữ liệu thật đều nằm ở phía server.
 */
(function () {
    "use strict";

    /** Tự ẩn thông báo thành công sau ít giây cho đỡ che nội dung. */
    function autoDismissAlerts() {
        var alerts = document.querySelectorAll(".alert-success.alert-dismissible");
        Array.prototype.forEach.call(alerts, function (alert) {
            window.setTimeout(function () {
                if (window.bootstrap && window.bootstrap.Alert) {
                    window.bootstrap.Alert.getOrCreateInstance(alert).close();
                }
            }, 6000);
        });
    }

    /** Chặn double-click gửi trùng đơn ứng tuyển / trùng tin tuyển dụng. */
    function preventDoubleSubmit() {
        var forms = document.querySelectorAll("form[method='post']");
        Array.prototype.forEach.call(forms, function (form) {
            form.addEventListener("submit", function () {
                var buttons = form.querySelectorAll("button[type='submit']");
                window.setTimeout(function () {
                    Array.prototype.forEach.call(buttons, function (button) {
                        if (!button.disabled) {
                            button.setAttribute("data-submitting", "true");
                            button.disabled = true;
                        }
                    });
                }, 0);
            });
        });
    }

    // Back có thể khôi phục cả nút đã khóa trong bộ nhớ trang của trình duyệt.
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            var buttons = document.querySelectorAll("button[data-submitting]");
            Array.prototype.forEach.call(buttons, function (button) {
                button.disabled = false;
                button.removeAttribute("data-submitting");
            });
        }
    });

    /**
     * Cảnh báo sớm khi CV vượt 5MB hoặc không phải PDF.
     * Server vẫn kiểm tra lại bằng apps/core/validators.py.
     */
    function warnOnInvalidCv() {
        var MAX_SIZE = 5 * 1024 * 1024;
        var inputs = document.querySelectorAll("input[type='file'][accept*='pdf']");

        Array.prototype.forEach.call(inputs, function (input) {
            var hint = document.createElement("div");
            hint.className = "form-text text-danger d-none";
            input.parentNode.appendChild(hint);

            input.addEventListener("change", function () {
                var file = input.files && input.files[0];
                hint.classList.add("d-none");
                if (!file) {
                    return;
                }
                if (file.size > MAX_SIZE) {
                    hint.textContent = "CV không được lớn hơn 5MB.";
                    hint.classList.remove("d-none");
                } else if (file.type !== "application/pdf") {
                    hint.textContent = "CV phải là file PDF hợp lệ.";
                    hint.classList.remove("d-none");
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        autoDismissAlerts();
        preventDoubleSubmit();
        warnOnInvalidCv();
    });
})();
