# Use an official Python base image
FROM continuumio/miniconda3:latest

# Set the working directory
WORKDIR /app

# Copy the environment.yml file to the container
COPY environment.yml .

# Create and activate the Conda environment
RUN conda env create -f environment.yml && conda clean -afy

# Activate the environment by default
RUN echo "conda activate docgen" >> ~/.bashrc
ENV PATH /opt/conda/envs/docgen/bin:$PATH

# Copy the application code
COPY . .

# Expose the desired port
EXPOSE 8085

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085", "--reload", "--timeout-keep-alive", "300"]