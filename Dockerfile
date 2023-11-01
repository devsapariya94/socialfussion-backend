# Use the official Python 3.11 image as the base
FROM python:3.11

# Set the working directory inside the container
WORKDIR /app

# Copy all the files in your project directory to the container
COPY . /app

# Install any necessary dependencies from requirements.txt
RUN pip install -r requirements.txt

# Expose port 5000 to allow access to the Flask application
EXPOSE 5000

# Specify the command to run your Flask application
CMD ["python", "app.py"]