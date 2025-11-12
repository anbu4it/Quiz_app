"""
One-time admin script to clear production database via HTTP endpoint.
This creates a secure endpoint that requires a secret token.

Usage:
1. Set ADMIN_CLEAR_TOKEN in Render environment variables
2. Visit: https://your-app.onrender.com/admin/clear-database?token=YOUR_SECRET_TOKEN
3. Remove ADMIN_CLEAR_TOKEN after use to disable the endpoint
"""

import os

from flask import Blueprint, jsonify, request

from models import Score, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/clear-database", methods=["GET"])
def clear_database():
    """Clear all data from database. Requires ADMIN_CLEAR_TOKEN."""

    # Check if feature is enabled
    expected_token = os.getenv("ADMIN_CLEAR_TOKEN")
    if not expected_token:
        return (
            jsonify(
                {
                    "error": "Admin endpoint disabled",
                    "message": "Set ADMIN_CLEAR_TOKEN environment variable to enable this endpoint",
                }
            ),
            403,
        )

    # Verify token
    provided_token = request.args.get("token")
    if not provided_token or provided_token != expected_token:
        return jsonify({"error": "Unauthorized", "message": "Invalid or missing token"}), 401

    # Clear database
    try:
        num_scores = Score.query.delete()
        num_users = User.query.delete()
        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Database cleared successfully",
                    "deleted": {"scores": num_scores, "users": num_users},
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database error", "message": str(e)}), 500
